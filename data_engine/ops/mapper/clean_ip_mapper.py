import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('clean_ip_mapper')
class CleanIpMapper(Mapper):
    """Mapper to clean ipv4 and ipv6 address in text samples."""

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
            self.pattern = r'(?:(?:1[0-9][0-9]\.)|(?:2[0-4][0-9]\.)|'
            self.pattern += r'(?:25[0-5]\.)|(?:[1-9][0-9]\.)|(?:[0-9]\.))'
            self.pattern += r'{3}(?:(?:1[0-9][0-9])|(?:2[0-4][0-9])|'
            self.pattern += r'(?:25[0-5])|(?:[1-9][0-9])|(?:[0-9]))|'
            self.pattern += r'([\da-fA-F]{1,4}:){7}[\da-fA-F]{1,4}'  # ipv6
        else:
            self.pattern = pattern
            if ((len(pattern) > 2) and
                (pattern.startswith("r'") and pattern.endswith("'")
                 or pattern.startswith('r"') and pattern.endswith('"'))):
                self.pattern = pattern[2:-1]
        self.repl = repl
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def process(self, sample):
        # Track statistics
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1

        if not re.search(self.pattern, sample[self.text_key], flags=re.DOTALL):
            if getattr(self, 'enable_detailed_logging', False):
                self.unmodified_samples += 1
            return sample

        sample[self.text_key] = re.sub(pattern=self.pattern,
                                       repl=self.repl,
                                       string=sample[self.text_key],
                                       flags=re.DOTALL)
        
        if getattr(self, 'enable_detailed_logging', False):
            self.modified_samples += 1
        
        return sample

    @classmethod
    @property
    def description(cls):
        return """Mapper to clean ipv4 and ipv6 address in text samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample('ftp://example.com/188.46.244.216my-page.html', 
                      'ftp://example.com/my-page.html')

    @classmethod
    @property
    def init_params(cls):
        return None
    
    def run(self, dataset, *, exporter=None, tracer=None):
        """Override run method to add logging summary."""
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples = 0
            self.modified_samples = 0
            self.unmodified_samples = 0
        
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        
        return result
    
    def _log_mapper_summary(self):
        """Generate and log summary statistics."""
        try:
            from loguru import logger
            
            total = self.total_samples
            modified = self.modified_samples
            unmodified = self.unmodified_samples
            
            if total == 0:
                return
            
            self._log_line("="*60)
            self._log_line(f"[{self._name}] IP Address Cleaning Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with IP removed: {modified} ({modified/total*100:.2f}%)")
            self._log_line(f"Samples unchanged: {unmodified} ({unmodified/total*100:.2f}%)")
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
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(
                self.job_uid,
                message,
                operator_name=self._name,
                operator_index=self.pipline_index
            )