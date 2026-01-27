import heapq

from jsonargparse.typing import ClosedUnitInterval, PositiveInt

from data_engine.utils.common_utils import stats_to_number

from ..base_op import OPERATORS, Selector, Sample, Param, DataType


@OPERATORS.register_module('range_specified_field_selector')
class RangeSpecifiedFieldSelector(Selector):
    """Selector to select a range of samples based on the sorted
    specified field value from smallest to largest. """

    def __init__(self,
                 field_key: str = '',
                 lower_percentile: ClosedUnitInterval = None,
                 upper_percentile: ClosedUnitInterval = None,
                 lower_rank: PositiveInt = None,
                 upper_rank: PositiveInt = None,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param field_key: Selector based on the specified value
            corresponding to the target key. The target key
            corresponding to multi-level field information need to be
            separated by '.'.
        :param lower_percentile: The lower bound of the percentile to
            be sample, samples will be selected if their specified field
            values are greater than this lower bound. When both
            lower_percentile and lower_rank are set, the value corresponding
            to the larger number of samples will be applied.
        :param upper_percentile: The upper bound of the percentile to
            be sample, samples will be selected if their specified field
            values are less or equal to the upper bound. When both
            upper_percentile and upper_rank are set, the value corresponding
            to the smaller number of samples will be applied.
        :param lower_rank: The lower bound of the rank to be sample,
            samples will be selected if their specified field values are
            greater than this lower bound. When both lower_percentile and
            lower_rank are set, the value corresponding to the larger number
            of samples will be applied.
        :param upper_rank: The upper bound of the rank to be sample,
            samples will be selected if their specified field values are
            less or equal to the upper bound. When both upper_percentile and
            upper_rank are set, the value corresponding to the smaller number
            of samples will be applied.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.field_key = field_key
        self.lower_percentile = lower_percentile
        self.upper_percentile = upper_percentile
        self.lower_rank = lower_rank
        self.upper_rank = upper_rank
        
        # Enable detailed logging for this selector
        self.enable_detailed_logging = True

    def process(self, dataset):
        # Store original dataset size for logging
        original_size = len(dataset)
        
        if len(dataset) <= 1 or not self.field_key:
            if getattr(self, 'enable_detailed_logging', False):
                self._log_selector_summary(original_size, original_size, 0, 0, 0, None, None)
            return dataset

        if self.lower_percentile is None and self.lower_rank is None:
            if getattr(self, 'enable_detailed_logging', False):
                self._log_selector_summary(original_size, original_size, 0, 0, 0, None, None)
            return dataset
        if self.upper_percentile is None and self.upper_rank is None:
            if getattr(self, 'enable_detailed_logging', False):
                self._log_selector_summary(original_size, original_size, 0, 0, 0, None, None)
            return dataset

        lower_bound, upper_bound = 0, len(dataset)
        if self.lower_percentile is not None:
            lower_bound = int(self.lower_percentile * len(dataset))
        if self.lower_rank is not None:
            lower_bound = max(lower_bound, self.lower_rank)
        if self.upper_percentile is not None:
            upper_bound = int(self.upper_percentile * len(dataset))
        if self.upper_rank is not None:
            upper_bound = min(upper_bound, self.upper_rank)
        upper_bound = max(lower_bound, upper_bound)

        field_keys = self.field_key.split('.')
        assert field_keys[0] in dataset.features.keys(
        ), "'{}' not in {}".format(field_keys[0], dataset.features.keys())

        def get_field_value_list(cur_dataset, field_keys):
            if len(field_keys) == 1:
                field_value_list = cur_dataset[field_keys[0]]
            else:
                field_value_list = []
                for item in cur_dataset[field_keys[0]]:
                    field_value = item
                    for key in field_keys[1:]:
                        assert key in field_value.keys(
                        ), "'{}' not in {}".format(key, field_value.keys())
                        field_value = field_value[key]
                    field_value_list.append(field_value)
            field_value_list = [stats_to_number(s) for s in field_value_list]
            return field_value_list

        field_value_list = get_field_value_list(dataset, field_keys)
        select_index = heapq.nsmallest(int(upper_bound), range(len(dataset)),
                                       field_value_list.__getitem__)
        sub_dataset = dataset.select(select_index)

        field_value_list = get_field_value_list(sub_dataset, field_keys)
        select_index = heapq.nlargest(int(upper_bound - lower_bound),
                                      range(len(sub_dataset)),
                                      field_value_list.__getitem__)

        selected_dataset = sub_dataset.select(select_index)
        
        # Generate detailed logging if enabled
        if getattr(self, 'enable_detailed_logging', False):
            selected_size = len(selected_dataset)
            # Get min and max values from selected dataset
            final_field_values = get_field_value_list(selected_dataset, field_keys)
            min_val = min(final_field_values) if final_field_values else None
            max_val = max(final_field_values) if final_field_values else None
            self._log_selector_summary(original_size, selected_size,
                                      original_size - selected_size,
                                      lower_bound, upper_bound, min_val, max_val)
        
        return selected_dataset

    @classmethod
    @property
    def description(cls):
        return """Selector to select a range of samples based on the sorted
    specified field value from smallest to largest. """

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
            Param("lower_percentile", DataType.ClosedUnitInterval, None, None),
            Param("upper_percentile", DataType.ClosedUnitInterval, None, None),
            Param("lower_rank", DataType.PositiveFloat, None, None),
            Param("upper_rank", DataType.PositiveFloat, None, None),
        ]
    
    def _log_selector_summary(self, total, selected, filtered, lower_bound, upper_bound, min_val, max_val):
        """
        Generate and log summary statistics for range-based selection.
        
        :param total: Total number of samples before selection
        :param selected: Number of samples selected
        :param filtered: Number of samples filtered out
        :param lower_bound: Lower bound rank
        :param upper_bound: Upper bound rank
        :param min_val: Minimum field value in selected samples
        :param max_val: Maximum field value in selected samples
        """
        try:
            from loguru import logger
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            
            # Output logs line by line for better display in UI
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Range Selection Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples: {total}")
            self._log_line(f"Selected samples: {selected} ({selected/total*100:.2f}%)")
            self._log_line(f"Filtered samples: {filtered} ({filtered/total*100:.2f}%)")
            self._log_line("")
            self._log_line(f"Selection range: rank {lower_bound} to {upper_bound}")
            
            if min_val is not None and max_val is not None:
                self._log_line(f"Field value range: {min_val:.4f} to {max_val:.4f}")
            
            # Add selector-specific parameters
            self._log_line("")
            self._log_line("Selector parameters:")
            self._log_line(f"  - Field key: {self.field_key}")
            if self.lower_percentile is not None:
                self._log_line(f"  - Lower percentile: {self.lower_percentile} ({self.lower_percentile*100:.1f}%)")
            if self.upper_percentile is not None:
                self._log_line(f"  - Upper percentile: {self.upper_percentile} ({self.upper_percentile*100:.1f}%)")
            if self.lower_rank is not None:
                self._log_line(f"  - Lower rank: {self.lower_rank}")
            if self.upper_rank is not None:
                self._log_line(f"  - Upper rank: {self.upper_rank}")
            
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