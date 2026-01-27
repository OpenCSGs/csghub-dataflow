from typing import List, Tuple, Union

from data_engine.utils.constant import Fields

from ..base_op import OPERATORS, Filter, Sample, Param, DataType


@OPERATORS.register_module('suffix_filter')
class SuffixFilter(Filter):
    """Filter to keep samples with specified suffix."""

    def __init__(self,
                 suffixes: Union[str, List[str], Tuple[str]] = [],
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param suffixes: the suffix of text that will be keep.
            For example: '.txt', 'txt' or ['txt', '.pdf', 'docx']
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        if suffixes is None:
            self.suffixes = []
        elif isinstance(suffixes, str):
            self.suffixes = [suffixes]
        else:
            self.suffixes = suffixes
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

    def compute_stats(self, sample):
        # suffix_filter doesn't compute stats, but we add detail for logging
        suffix = sample.get(Fields.suffix, '')
        
        # Determine filter result
        if self.suffixes:
            keep = suffix in self.suffixes
            reason = 'kept' if keep else 'suffix_not_match'
        else:
            keep = True
            reason = 'kept'
        
        # Store detailed information for logging
        sample[Fields.stats]['suffix_filter_detail'] = {
            'suffix': suffix,
            'keep': keep,
            'reason': reason,
            'allowed_suffixes': str(self.suffixes)
        }
        
        return sample

    def process(self, sample):
        if self.suffixes:
            if sample[Fields.suffix] in self.suffixes:
                return True
            else:
                return False
        else:
            return True
    @classmethod
    @property
    def description(cls):
        return """Filter to keep samples with specified suffix."""

    @classmethod
    @property
    def sample(cls):
        return Sample("{"
            "'text': '中文也是一个字算一个长度',"
            "Fields.suffix: '.txt'"
        "}", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("suffixes", DataType.LIST, None, []),
        ]
    
    def run(self, dataset, *, exporter=None, tracer=None):
        """Override run method to add detailed logging."""
        from data_engine.utils.constant import Fields
        from data_engine.core.data import add_same_content_to_new_column
        
        # Add stats column if not exists
        if Fields.stats not in dataset.features:
            dataset = dataset.map(add_same_content_to_new_column,
                                  fn_kwargs={
                                      'new_column_name': Fields.stats,
                                      'initial_value': {}
                                  },
                                  num_proc=self.runtime_np(),
                                  desc='Adding new column for stats')
        
        # Compute stats for all samples
        dataset_with_stats = dataset.map(self.compute_stats,
                                        num_proc=self.runtime_np(),
                                        with_rank=self.use_cuda(),
                                        desc=self._name + '_compute_stats')
        
        # Export stats if needed
        if self.stats_export_path is not None:
            exporter.export_compute_stats(dataset_with_stats, self.stats_export_path)
        
        # Filter dataset
        filtered_dataset = dataset_with_stats.filter(self.process,
                                                    num_proc=self.runtime_np(),
                                                    desc=self._name + '_process')
        
        # Trace if needed
        if tracer:
            tracer.trace_filter(self._name, dataset_with_stats, filtered_dataset,
                               job_uid=self.job_uid, pipeline_index=self.pipline_index)
        
        # Log detailed statistics
        if getattr(self, 'enable_detailed_logging', False):
            self._log_filter_details(dataset_with_stats, filtered_dataset)
        
        return filtered_dataset
    
    def _log_filter_details(self, original_dataset, filtered_dataset):
        try:
            from loguru import logger
            from data_engine.utils.constant import Fields
            total_samples = len(original_dataset)
            stats_counters = {'total': total_samples, 'kept': 0, 'suffix_not_match': 0}
            for sample in original_dataset:
                stats = sample.get(Fields.stats, {})
                detail_key = 'suffix_filter_detail'
                if detail_key in stats:
                    reason = stats[detail_key].get('reason', 'unknown')
                    stats_counters[reason] = stats_counters.get(reason, 0) + 1
            self._log_summary_statistics(stats_counters)
        except Exception as e:
            import traceback
            logger.error(f"Failed to generate detailed logging: {e}\n{traceback.format_exc()}")
    
    def _log_summary_statistics(self, stats_counters):
        total = stats_counters['total']
        kept = stats_counters['kept']
        filtered = total - kept
        self._log_line("="*60)
        self._log_line(f"[{self._name}] Filter Summary Statistics")
        self._log_line("="*60)
        self._log_line(f"Total samples: {total}")
        self._log_line(f"Kept samples: {kept} ({kept/total*100:.2f}%)")
        self._log_line(f"Filtered samples: {filtered} ({filtered/total*100:.2f}%)")
        if filtered > 0:
            self._log_line("")
            self._log_line("Filtered breakdown:")
            if stats_counters.get('suffix_not_match', 0) > 0:
                self._log_line(f"  - Suffix not match: {stats_counters['suffix_not_match']} ({stats_counters['suffix_not_match']/total*100:.2f}%)")
        self._log_line("")
        self._log_line("Filter parameters:")
        self._log_line(f"  - Allowed suffixes: {self.suffixes}")
        self._log_line("="*60)
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)