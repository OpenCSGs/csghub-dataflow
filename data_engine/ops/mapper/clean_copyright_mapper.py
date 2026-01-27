# Some code here has been modified from:
# https://github.com/togethercomputer/RedPajama-Data/tree/rp_v1/
# --------------------------------------------------------

import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('clean_copyright_mapper')
class CleanCopyrightMapper(Mapper):
    """Mapper to clean copyright comments at the beginning of the text
    samples."""

    def __init__(self, *args, **kwargs):
        """
        Initialization method.

        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.pat = re.compile('/\\*[^*]*\\*+(?:[^/*][^*]*\\*+)*/')
        self.cpat = re.compile('copyright', re.IGNORECASE)
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def process(self, sample):
        # Track statistics
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        
        original_text = sample[self.text_key]

        r = self.pat.search(sample[self.text_key])
        if r:
            # found one, now see if it contains "copyright", if so strip it
            span = r.span()
            sub = sample[self.text_key][span[0]:span[1]]
            if self.cpat.search(sub):
                # cut it
                sample[self.text_key] = sample[
                    self.text_key][:span[0]] + sample[self.text_key][span[1]:]

            # Track if modified
            if getattr(self, 'enable_detailed_logging', False):
                if sample[self.text_key] != original_text:
                    self.modified_samples += 1
                else:
                    self.unmodified_samples += 1
            return sample

        lines = sample[self.text_key].split('\n')
        skip = 0

        # Greedy replace any file that begins with comment block, most
        # are copyright headers
        for k in range(len(lines)):
            if (lines[k].startswith('//') or lines[k].startswith('#')
                    or lines[k].startswith('--') or not lines[k]):
                skip = skip + 1
            else:
                break

        if skip:
            # we skipped, consume it
            sample[self.text_key] = '\n'.join(lines[skip:])
        
        # Track if modified
        if getattr(self, 'enable_detailed_logging', False):
            if sample[self.text_key] != original_text:
                self.modified_samples += 1
            else:
                self.unmodified_samples += 1
        
        return sample
    @classmethod
    @property
    def description(cls):
        return """Mapper to clean copyright comments at the beginning of the text
    samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample("这是一段 /* 多行注释\n注释内容copyright\n*/ 的文本。另外还有一些 // 单行注释。", 
                      "这是一段  的文本。另外还有一些 // 单行注释。")

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
            self._log_line(f"[{self._name}] Copyright Cleaning Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with copyright removed: {modified} ({modified/total*100:.2f}%)")
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