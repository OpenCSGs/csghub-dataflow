import networkx as nx
import numpy as np
from loguru import logger

from data_engine.utils.constant import HashKeys
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
                 similarity_threshold: float = 0.95,
                 nn_indices_key: str = 'nn_indices',
                 nn_scores_key: str = 'nn_scores',
                 *args, 
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.similarity_threshold = similarity_threshold
        self.nn_indices_key = nn_indices_key
        self.nn_scores_key = nn_scores_key

    def compute_hash(self, sample):
        # This method is a placeholder to fit the framework.
        # The actual logic doesn't rely on this hash.
        if self.nn_indices_key not in sample or self.nn_scores_key not in sample:
            sample[self.nn_indices_key] = [[]]
            sample[self.nn_scores_key] = [[]]
        sample[HashKeys.similarity_hash] = f"similarity_data_{id(sample)}"
        return sample

    def process(self, dataset, show_num=0):
        if len(dataset) <= 1:
            return dataset, {}

        # Convert dataset to pandas DataFrame for easier graph processing
        df = dataset.to_pandas()

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

        return filtered_dataset, dup_pairs

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
            Param("similarity_threshold", DataType.FLOAT, {}, 0.95),
            Param("nn_indices_key", DataType.STRING, {}, "nn_indices"),
            Param("nn_scores_key", DataType.STRING, {}, "nn_scores"),
        ]
