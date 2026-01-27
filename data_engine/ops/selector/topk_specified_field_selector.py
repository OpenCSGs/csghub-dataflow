import heapq

from jsonargparse.typing import ClosedUnitInterval, PositiveInt

from data_engine.utils.common_utils import stats_to_number

from ..base_op import OPERATORS, Selector, Sample, Param, DataType


@OPERATORS.register_module('topk_specified_field_selector')
class TopkSpecifiedFieldSelector(Selector):
    """Selector to select top samples based on the sorted specified field
    value."""

    def __init__(self,
                 field_key: str = '',
                 top_ratio: ClosedUnitInterval = None,
                 topk: PositiveInt = None,
                 reverse: bool = True,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param field_key: Selector based on the specified value
            corresponding to the target key. The target key
            corresponding to multi-level field information need to be
            separated by '.'.
        :param top_ratio: Ratio of selected top samples, samples will be
            selected if their specified field values are within this
            parameter. When both topk and top_ratio are set, the value
            corresponding to the smaller number of samples will be
            applied.
        :param topk: Number of selected top sample, samples will be
            selected if their specified field values are within this
            parameter. When both topk and top_ratio are set, the value
            corresponding to the smaller number of samples will be
            applied.
        :param reverse: Determine the sorting rule, if reverse=True,
            then sort in descending order.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.field_key = field_key
        self.top_ratio = top_ratio
        self.topk = topk
        self.reverse = reverse
        
        # Enable detailed logging for this selector
        self.enable_detailed_logging = True

    def process(self, dataset):
        # Store original dataset size for logging
        original_size = len(dataset)
        
        if len(dataset) <= 1 or not self.field_key:
            if getattr(self, 'enable_detailed_logging', False):
                self._log_selector_summary(original_size, original_size, 0, 0, None, None)
            return dataset

        select_num = 0
        if not self.top_ratio:
            if not self.topk:
                if getattr(self, 'enable_detailed_logging', False):
                    self._log_selector_summary(original_size, original_size, 0, 0, None, None)
                return dataset
            else:
                select_num = self.topk
        else:
            select_num = self.top_ratio * len(dataset)
            if self.topk and self.topk < select_num:
                select_num = self.topk

        field_keys = self.field_key.split('.')
        assert field_keys[0] in dataset.features.keys(
        ), "'{}' not in {}".format(field_keys[0], dataset.features.keys())

        if len(field_keys) == 1:
            field_value_list = dataset[field_keys[0]]
        else:
            field_value_list = []
            for item in dataset[field_keys[0]]:
                field_value = item
                for key in field_keys[1:]:
                    assert key in field_value.keys(), "'{}' not in {}".format(
                        key, field_value.keys())
                    field_value = field_value[key]
                field_value_list.append(
                    stats_to_number(field_value, self.reverse))

        if self.reverse:
            select_index = heapq.nlargest(int(select_num), range(len(dataset)),
                                          field_value_list.__getitem__)
        else:
            select_index = heapq.nsmallest(int(select_num),
                                           range(len(dataset)),
                                           field_value_list.__getitem__)
        
        selected_dataset = dataset.select(select_index)
        
        # Generate detailed logging if enabled
        if getattr(self, 'enable_detailed_logging', False):
            selected_size = len(selected_dataset)
            # Get min and max values from selected samples
            selected_values = [field_value_list[i] for i in select_index]
            min_val = min(selected_values) if selected_values else None
            max_val = max(selected_values) if selected_values else None
            self._log_selector_summary(original_size, selected_size,
                                      original_size - selected_size,
                                      select_num, min_val, max_val)
        
        return selected_dataset

    @classmethod
    @property
    def description(cls):
        return """Selector to select top samples based on the sorted specified field
    value."""

    @classmethod
    @property
    def sample(cls):
        return Sample("{"
            "'text': '，。、„”“«»１」「《》´∶：？！',"
            "'count': None,"
            "'meta': {"
            "    'suffix': '.html',"
            "    'key1': {"
            "        'key2': {"
            "            'count': 18"
            "        },"
            "        'count': 48"
            "    }"
            "}"
        "}", 
                      "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("field_key", DataType.STRING, None, ''),
            Param("top_ratio", DataType.ClosedUnitInterval, None, None),
            Param("topk", DataType.PositiveFloat, None, None),
            Param("reverse", DataType.BOOLEAN, None, True),
        ]
    
    def _log_selector_summary(self, total, selected, filtered, target_num, min_val, max_val):
        """
        Generate and log summary statistics for topk selection.
        
        :param total: Total number of samples before selection
        :param selected: Number of samples selected
        :param filtered: Number of samples filtered out
        :param target_num: Target number of samples to select
        :param min_val: Minimum field value in selected samples
        :param max_val: Maximum field value in selected samples
        """
        try:
            from loguru import logger
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            
            # Output logs line by line for better display in UI
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Top-K Selection Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples: {total}")
            self._log_line(f"Selected samples: {selected} ({selected/total*100:.2f}%)")
            self._log_line(f"Filtered samples: {filtered} ({filtered/total*100:.2f}%)")
            
            if min_val is not None and max_val is not None:
                self._log_line("")
                if self.reverse:
                    self._log_line(f"Selected field value range (descending):")
                    self._log_line(f"  - Highest: {max_val:.4f}")
                    self._log_line(f"  - Lowest: {min_val:.4f}")
                else:
                    self._log_line(f"Selected field value range (ascending):")
                    self._log_line(f"  - Lowest: {min_val:.4f}")
                    self._log_line(f"  - Highest: {max_val:.4f}")
            
            # Add selector-specific parameters
            self._log_line("")
            self._log_line("Selector parameters:")
            self._log_line(f"  - Field key: {self.field_key}")
            if self.top_ratio is not None:
                self._log_line(f"  - Top ratio: {self.top_ratio} ({self.top_ratio*100:.1f}%)")
            if self.topk is not None:
                self._log_line(f"  - Top K: {self.topk}")
            self._log_line(f"  - Reverse (descending): {self.reverse}")
            self._log_line(f"  - Target selection: {int(target_num)} samples")
            
            self._log_line("="*60)
            
        except Exception as e:
            import traceback
            error_msg = f"Failed to generate selector logging: {e}\n{traceback.format_exc()}"
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