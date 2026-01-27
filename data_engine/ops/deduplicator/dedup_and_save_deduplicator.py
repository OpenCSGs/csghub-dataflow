import networkx as nx
import numpy as np
from loguru import logger

from data_engine.utils.constant import HashKeys, Fields, StatsKeys
from ..base_op import OPERATORS, Deduplicator, Sample, Param, DataType

OP_NAME = 'dedup_and_save_deduplicator'


@OPERATORS.register_module(OP_NAME)
class DedupAndSaveDeduplicator(Deduplicator):
    """
    Deduplicator based on graph connectivity. Samples with similarity scores
    above a threshold are connected in a graph, and only one sample from
    each connected component is kept.
    """

    def __init__(self, 
                 similarity_threshold: float = 0.5,
                 nn_indices_key: str = 'nn_indices',
                 nn_scores_key: str = 'nn_scores',
                 fields_to_filter: list = None,
                 *args, 
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.similarity_threshold = similarity_threshold
        self.nn_indices_key = nn_indices_key
        self.nn_scores_key = nn_scores_key
        self.fields_to_filter = fields_to_filter or ['embedding', 'nn_indices', 'nn_scores', 'text', 'instruction', 'response']
        
        # Enable detailed logging for this deduplicator
        self.enable_detailed_logging = True

    def compute_hash(self, sample):
        # This method is a placeholder to fit the framework.
        # The actual logic doesn't rely on this hash.
        if self.nn_indices_key not in sample or self.nn_scores_key not in sample:
            sample[self.nn_indices_key] = [[]]
            sample[self.nn_scores_key] = [[]]
        # Do not create the similarity_hash field because the actual deduplication logic does not require it
        # sample[HashKeys.similarity_hash] = f"similarity_data_{id(sample)}"
        return sample

    def process(self, dataset, show_num=0):
        # Store original dataset size for logging
        original_size = len(dataset)
        
        print(f"[dedup_and_save_deduplicator] Input: {original_size} samples")
        
        if len(dataset) <= 1:
            print(f"[dedup_and_save_deduplicator] Output: {len(dataset)} samples (no deduplication needed)")
            if getattr(self, 'enable_detailed_logging', False):
                self._log_dedup_summary(original_size, original_size, 0, 0)
            return dataset, {}

        # Convert dataset to pandas DataFrame for easier graph processing
        df = dataset.to_pandas()
        print(f"[dedup_and_save_deduplicator] Processing similarity graph with threshold: {self.similarity_threshold}")

        # Create a graph and add all samples as nodes
        G = nx.Graph()
        G.add_nodes_from(df.index)

        # Build the graph by adding edges between similar samples
        for index, row in df.iterrows():
            indices = row.get(self.nn_indices_key, [])
            scores = row.get(self.nn_scores_key, [])

            # ([[1, 2]] -> [1, 2])
            # ([[1, 2][4, 5] -> [1,2])
            if (hasattr(indices, 'size') and indices.size > 0 or isinstance(indices, list) and len(indices) > 0) and isinstance(indices[0], (list, np.ndarray)):
                indices = indices[0]
            if (hasattr(scores, 'size') and scores.size > 0 or isinstance(scores, list) and len(scores) > 0) and isinstance(scores[0], (list, np.ndarray)):
                scores = scores[0]

            for neighbor_idx, score in zip(indices, scores):
                # Cast numpy numeric types to native python int to avoid hash errors
                neighbor_idx = int(neighbor_idx)
                if score >= self.similarity_threshold and neighbor_idx in df.index:
                    G.add_edge(index, neighbor_idx)

        # Find all connected components in the graph
        connected_components = list(nx.connected_components(G))

        # For each component, keep only the sample with the minimum index
        to_keep_indices = {min(component) for component in connected_components}

        # The indices in `to_keep_indices` are DataFrame indices, which are the original
        # integer positions. We can use them directly with `dataset.select`.
        indices_to_keep = sorted(list(to_keep_indices))

        # Filter the original dataset to keep only the selected samples
        filtered_dataset = dataset.select(indices_to_keep)
        print(f"[dedup_and_save_deduplicator] Output: {len(filtered_dataset)} samples after deduplication (removed {len(dataset) - len(filtered_dataset)} duplicates)")

        # For tracing, sample some duplicate pairs from components with more than one member
        dup_pairs = {}
        if show_num > 0:
            processed_components = 0
            for component in connected_components:
                if len(component) > 1 and processed_components < show_num:
                    sorted_component = sorted(list(component))
                    group_key = f"group_{sorted_component[0]}"
                    dup_pairs[group_key] = [dataset[i] for i in sorted_component[:2]]
                    processed_components += 1

        print(f"[dedup_and_save_deduplicator] Found {len(connected_components)} connected components")

        # Unified processing of field filtering - Move the specified field to stats
        def move_fields_to_stats(sample):
            if Fields.stats not in sample:
                sample[Fields.stats] = {}

            # move_the_specified_field_to_stats
            for field in self.fields_to_filter:
                if field in sample:
                    # Obtain the corresponding StatsKeys constant based on the field name
                    stats_key = getattr(StatsKeys, field, field)
                    sample[Fields.stats][stats_key] = sample[field]
                    del sample[field]
            
            return sample

        # applicationFieldFiltering
        final_dataset = filtered_dataset.map(move_fields_to_stats)
        print(f"[dedup_and_save_deduplicator] Filtered fields {self.fields_to_filter} to stats")
        
        # Generate detailed logging if enabled
        if getattr(self, 'enable_detailed_logging', False):
            deduplicated_size = len(final_dataset)
            self._log_dedup_summary(original_size, deduplicated_size,
                                   original_size - deduplicated_size,
                                   len(connected_components))
        
        return final_dataset, dup_pairs

    @classmethod
    @property
    def description(cls):
        return "A deduplicator based on graph connectivity. It constructs a similarity graph by connecting " \
               "samples with similarity scores above the threshold, then keeps only one sample (with minimum " \
               "index) from each connected component. Suitable for datasets with pre-computed nearest neighbor " \
               "similarity information."

    @classmethod
    @property
    def sample(cls):
        return Sample(
            before="[" \
                   "{'text': 'The cat sat on the mat', 'nn_indices': [[1, 2]], 'nn_scores': [[0.97, 0.89]]}," \
                   "{'text': 'A cat was sitting on a mat', 'nn_indices': [[0, 2]], 'nn_scores': [[0.97, 0.92]]}," \
                   "{'text': 'The cat sat on the mat', 'nn_indices': [[0, 1]], 'nn_scores': [[0.89, 0.92]]}," \
                   "{'text': 'Today is a sunny day', 'nn_indices': [[]], 'nn_scores': [[]]}" \
                   "]",
            after="[" \
                  "{'text': 'The cat sat on the mat', 'nn_indices': [[1, 2]], 'nn_scores': [[0.97, 0.89]]}," \
                  "{'text': 'Today is a sunny day', 'nn_indices': [[]], 'nn_scores': [[]]}" \
                  "]"
        )

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("similarity_threshold", DataType.FLOAT, {}, 0.5),
            Param("nn_indices_key", DataType.STRING, {}, "nn_indices"),
            Param("nn_scores_key", DataType.STRING, {}, "nn_scores"),
            Param("fields_to_filter", DataType.LIST, {}, ["embedding", "nn_indices", "nn_scores", "text", "instruction", "response"]),
        ]
    
    def _log_dedup_summary(self, total, kept, removed, num_components):
        """
        Generate and log summary statistics for graph-based deduplication.
        
        :param total: Total number of documents before deduplication
        :param kept: Number of unique documents kept
        :param removed: Number of duplicate documents removed
        :param num_components: Number of connected components found
        """
        try:
            from loguru import logger
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            
            # Output logs line by line for better display in UI
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Graph-Based Deduplication Summary")
            self._log_line("="*60)
            self._log_line(f"Total documents: {total}")
            self._log_line(f"Unique documents kept: {kept} ({kept/total*100:.2f}%)")
            self._log_line(f"Duplicate documents removed: {removed} ({removed/total*100:.2f}%)")
            self._log_line("")
            self._log_line(f"Connected components found: {num_components}")
            
            # Add deduplicator-specific parameters
            self._log_line("")
            self._log_line("Deduplicator parameters:")
            self._log_line(f"  - Similarity threshold: {self.similarity_threshold}")
            self._log_line(f"  - NN indices key: {self.nn_indices_key}")
            self._log_line(f"  - NN scores key: {self.nn_scores_key}")
            self._log_line(f"  - Fields to filter: {self.fields_to_filter}")
            self._log_line(f"  - Algorithm: Graph connectivity")
            
            self._log_line("="*60)
            
        except Exception as e:
            import traceback
            error_msg = f"Failed to generate graph deduplication logging: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            if hasattr(self, 'job_uid') and self.job_uid:
                from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_error
                insert_pipline_job_run_task_log_error(
                    self.job_uid,
                    error_msg,
                    operator_name=self._name,
                    operator_index=self.pipline_index
                )
    
    def _log_line(self, message):
        """Log a single line to both logger and MongoDB."""
        from loguru import logger
        logger.info(message)
        # Only write to MongoDB if job_uid exists
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(
                self.job_uid,
                message,
                operator_name=self._name,
                operator_index=self.pipline_index
            )
