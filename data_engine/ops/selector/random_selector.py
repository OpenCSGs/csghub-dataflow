from jsonargparse.typing import ClosedUnitInterval, PositiveInt

from data_engine.format.mixture_formatter import MixtureFormatter

from ..base_op import OPERATORS, Selector, Sample, Param, DataType


@OPERATORS.register_module('random_selector')
class RandomSelector(Selector):
    """Selector to random select samples. """

    def __init__(self,
                 select_ratio: ClosedUnitInterval = None,
                 select_num: PositiveInt = None,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param select_ratio: The ratio to select. When both
            select_ratio and select_num are set, the value corresponding
            to the smaller number of samples will be applied.
        :param select_num: The number of samples to select. When both
            select_ratio and select_num are set, the value corresponding
            to the smaller number of samples will be applied.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.select_ratio = select_ratio
        self.select_num = select_num
        
        # Enable detailed logging for this selector
        self.enable_detailed_logging = True

    def process(self, dataset):
        # Store original dataset size for logging
        original_size = len(dataset)
        
        if len(dataset) <= 1:
            if getattr(self, 'enable_detailed_logging', False):
                self._log_selector_summary(original_size, original_size, 0, 0)
            return dataset

        if self.select_ratio is None and self.select_num is None:
            if getattr(self, 'enable_detailed_logging', False):
                self._log_selector_summary(original_size, original_size, 0, 0)
            return dataset

        select_num = 0
        if not self.select_ratio:
            select_num = self.select_num
        else:
            select_num = int(self.select_ratio * len(dataset))
            if self.select_num and self.select_num < select_num:
                select_num = self.select_num

        selected_dataset = MixtureFormatter.random_sample(dataset,
                                              sample_number=select_num)
        
        # Generate detailed logging if enabled
        if getattr(self, 'enable_detailed_logging', False):
            selected_size = len(selected_dataset)
            self._log_selector_summary(original_size, selected_size,
                                      original_size - selected_size, select_num)
        
        return selected_dataset

    @classmethod
    @property
    def description(cls):
        return """Selector to random select samples. """

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
            Param("select_ratio", DataType.ClosedUnitInterval, None, None),
            Param("select_num", DataType.PositiveFloat, None, None),
        ]
    
    def _log_selector_summary(self, total, selected, filtered, target_num):
        """
        Generate and log summary statistics for random selection.
        
        :param total: Total number of samples before selection
        :param selected: Number of samples selected
        :param filtered: Number of samples filtered out
        :param target_num: Target number of samples to select
        """
        try:
            from loguru import logger
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            
            # Output logs line by line for better display in UI
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Random Selection Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples: {total}")
            self._log_line(f"Selected samples: {selected} ({selected/total*100:.2f}%)")
            self._log_line(f"Filtered samples: {filtered} ({filtered/total*100:.2f}%)")
            
            # Add selector-specific parameters
            self._log_line("")
            self._log_line("Selector parameters:")
            if self.select_ratio is not None:
                self._log_line(f"  - Select ratio: {self.select_ratio} ({self.select_ratio*100:.1f}%)")
            if self.select_num is not None:
                self._log_line(f"  - Select num: {self.select_num}")
            self._log_line(f"  - Target selection: {target_num} samples")
            self._log_line(f"  - Selection method: Random sampling")
            
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