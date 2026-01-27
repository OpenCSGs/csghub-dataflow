import numbers

from jsonargparse.typing import ClosedUnitInterval, PositiveInt

from ..base_op import OPERATORS, Selector, Sample, Param, DataType


@OPERATORS.register_module('frequency_specified_field_selector')
class FrequencySpecifiedFieldSelector(Selector):
    """Selector to select samples based on the sorted frequency of specified
    field."""

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
        :param top_ratio: Ratio of selected top specified field value,
            samples will be selected if their specified field values are
            within this parameter. When both topk and top_ratio are set,
            the value corresponding to the smaller number of samples
            will be applied.
        :param topk: Number of selected top specified field value,
            samples will be selected if their specified field values are
            within this parameter. When both topk and top_ratio are set,
            the value corresponding to the smaller number of samples
            will be applied.
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
                self._log_selector_summary(original_size, original_size, 0, {})
            return dataset

        field_keys = self.field_key.split('.')
        assert field_keys[0] in dataset.features.keys(
        ), "'{}' not in {}".format(field_keys[0], dataset.features.keys())

        field_value_dict = {}
        for i, item in enumerate(dataset[field_keys[0]]):
            field_value = item
            for key in field_keys[1:]:
                assert key in field_value.keys(), "'{}' not in {}".format(
                    key, field_value.keys())
                field_value = field_value[key]
            assert field_value is None or isinstance(
                field_value, str) or isinstance(
                    field_value, numbers.Number
                ), 'The {} item is not String, Numbers or NoneType'.format(i)
            if field_value not in field_value_dict.keys():
                field_value_dict[field_value] = [i]
            else:
                field_value_dict[field_value].append(i)

        select_num = 0
        if not self.top_ratio:
            if not self.topk:
                if getattr(self, 'enable_detailed_logging', False):
                    self._log_selector_summary(original_size, original_size, 0, field_value_dict)
                return dataset
            else:
                select_num = self.topk
        else:
            select_num = self.top_ratio * len(field_value_dict)
            if self.topk and self.topk < select_num:
                select_num = self.topk

        select_index = sum(
            sorted(field_value_dict.values(),
                   key=lambda x: len(x),
                   reverse=self.reverse)[:int(select_num)], [])
        
        selected_dataset = dataset.select(select_index)
        
        # Generate detailed logging if enabled
        if getattr(self, 'enable_detailed_logging', False):
            selected_size = len(selected_dataset)
            self._log_selector_summary(original_size, selected_size,
                                      original_size - selected_size,
                                      field_value_dict)
        
        return selected_dataset

    @classmethod
    @property
    def description(cls):
        return """Selector to select samples based on the sorted frequency of specified
    field."""

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
    
    def _log_selector_summary(self, total, selected, filtered, field_value_dict):
        """
        Generate and log summary statistics for frequency-based selection.
        
        :param total: Total number of samples before selection
        :param selected: Number of samples selected
        :param filtered: Number of samples filtered out
        :param field_value_dict: Dictionary mapping field values to sample indices
        """
        try:
            from loguru import logger
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            
            # Calculate statistics
            unique_values = len(field_value_dict)
            
            # Find top field values by frequency
            sorted_values = sorted(field_value_dict.items(),
                                  key=lambda x: len(x[1]),
                                  reverse=self.reverse)
            
            # Output logs line by line for better display in UI
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Frequency Selection Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples: {total}")
            self._log_line(f"Selected samples: {selected} ({selected/total*100:.2f}%)")
            self._log_line(f"Filtered samples: {filtered} ({filtered/total*100:.2f}%)")
            self._log_line("")
            self._log_line(f"Unique field values: {unique_values}")
            
            # Show top field values
            if sorted_values:
                self._log_line("")
                self._log_line("Top field values by frequency:")
                for i, (value, indices) in enumerate(sorted_values[:5]):
                    value_str = str(value) if value is not None else "None"
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    self._log_line(f"  {i+1}. '{value_str}': {len(indices)} samples ({len(indices)/total*100:.2f}%)")
                
                if len(sorted_values) > 5:
                    self._log_line(f"  ... and {len(sorted_values) - 5} more values")
            
            # Add selector-specific parameters
            self._log_line("")
            self._log_line("Selector parameters:")
            self._log_line(f"  - Field key: {self.field_key}")
            if self.top_ratio is not None:
                self._log_line(f"  - Top ratio: {self.top_ratio} ({self.top_ratio*100:.1f}%)")
            if self.topk is not None:
                self._log_line(f"  - Top K: {self.topk}")
            self._log_line(f"  - Reverse (descending): {self.reverse}")
            
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