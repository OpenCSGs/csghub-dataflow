import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('remove_non_chinese_character_mapper')
class RemoveNonChineseCharacterlMapper(Mapper):
    """Mapper to remove non chinese Character in text samples."""

    def __init__(self,
                 keep_alphabet: bool = True,
                 keep_number: bool = True,
                 keep_punc: bool = True,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param keep_alphabet: whether to keep alphabet
        :param keep_number: whether to keep number
        :param keep_punc: whether to keep punctuation
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.pattern = u'[^\u4e00-\u9fa5'
        if keep_alphabet:
            self.pattern += u'A-Za-z'
        if keep_number:
            self.pattern += u'0-9'
        if keep_punc:
            self.pattern += u'.， ,\\-。%《*》/•、&＆(—)（+）：？!！“”·]+'
        else:
            self.pattern += u']'
        
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

        original_text = sample[self.text_key]
        
        sample[self.text_key] = re.sub(pattern=self.pattern,
                                       repl=r'',
                                       string=sample[self.text_key],
                                       flags=re.DOTALL)
        
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
        return """Mapper to remove non chinese Character in text samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample("👊    所有的非汉字a44sh都12@46h会被*&……*qb^4525去掉", 
                      "所有的非汉字都会被去掉")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("keep_alphabet", DataType.BOOLEAN, None, True),
            Param("keep_number", DataType.BOOLEAN, None, True),
            Param("keep_punc", DataType.BOOLEAN, None, True),
        ]
    
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
            self._log_line(f"[{self._name}] Non-Chinese Character Removal Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with non-Chinese chars removed: {modified} ({modified/total*100:.2f}%)")
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