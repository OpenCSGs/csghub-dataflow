import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('clean_email_mapper')
class CleanEmailMapper(Mapper):
    """Mapper to clean email in text samples."""

    def __init__(self, pattern: str = None, repl: str = '', *args, **kwargs):
        """
        Initialization method.

        :param pattern: regular expression pattern to search for within text.
        :param repl: replacement string, default is empty string.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        if pattern is None:
            self.pattern = r'[A-Za-z0-9.\-+_]+@[a-z0-9.\-+_]+\.[a-z]+'
        else:
            self.pattern = pattern
            if ((len(pattern) > 2) and
                (pattern.startswith("r'") and pattern.endswith("'")
                 or pattern.startswith('r"') and pattern.endswith('"'))):
                self.pattern = pattern[2:-1]

        self.repl = repl
        
        # Enable detailed logging for this mapper
        self.enable_detailed_logging = True
        # Statistics counters
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def process(self, sample):
        # Track statistics if logging is enabled
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1

        if not re.search(self.pattern, sample[self.text_key], flags=re.DOTALL):
            # No email found, sample unchanged
            if getattr(self, 'enable_detailed_logging', False):
                self.unmodified_samples += 1
            return sample

        # Email found, clean it
        sample[self.text_key] = re.sub(pattern=self.pattern,
                                       repl=self.repl,
                                       string=sample[self.text_key],
                                       flags=re.DOTALL)
        
        # Track modified samples
        if getattr(self, 'enable_detailed_logging', False):
            self.modified_samples += 1
        
        return sample

    @classmethod
    @property
    def description(cls):
        return "Mapper to clean email in text samples."

    @classmethod
    @property
    def sample(cls):
        return Sample("happy day euqdh@cjqi.com", "happy day ")

    @classmethod
    @property
    def init_params(cls):
        return None
    
    def run(self, dataset, *, exporter=None, tracer=None):
        """Override run method to add logging summary."""
        # Reset statistics
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples = 0
            self.modified_samples = 0
            self.unmodified_samples = 0
        
        # Call parent run method
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        
        # Generate detailed logging if enabled
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        
        return result
    
    def _log_mapper_summary(self):
        """Generate and log summary statistics for email cleaning."""
        try:
            from loguru import logger
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            
            total = self.total_samples
            modified = self.modified_samples
            unmodified = self.unmodified_samples
            
            if total == 0:
                return
            
            # Output logs line by line for better display in UI
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Email Cleaning Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with emails cleaned: {modified} ({modified/total*100:.2f}%)")
            self._log_line(f"Samples without emails: {unmodified} ({unmodified/total*100:.2f}%)")
            
            # Add mapper-specific parameters
            self._log_line("")
            self._log_line("Mapper parameters:")
            self._log_line(f"  - Pattern: {self.pattern}")
            self._log_line(f"  - Replacement: '{self.repl}'")
            
            self._log_line("="*60)
            
        except Exception as e:
            import traceback
            from loguru import logger
            error_msg = f"Failed to generate mapper logging: {e}\n{traceback.format_exc()}"
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
