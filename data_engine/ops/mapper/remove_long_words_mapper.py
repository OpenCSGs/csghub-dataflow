# Some code here has been modified from:
# https://huggingface.co/spaces/huggingface/text-data-filtering
# --------------------------------------------------------

import sys

from jsonargparse.typing import PositiveInt

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType
from ..common import (SPECIAL_CHARACTERS, merge_on_whitespace_tab_newline,
                      split_on_newline_tab_whitespace, strip)


@OPERATORS.register_module('remove_long_words_mapper')
class RemoveLongWordsMapper(Mapper):
    """Mapper to remove long words within a specific range."""

    def __init__(self,
                 min_len: PositiveInt = 1,
                 max_len: PositiveInt = sys.maxsize,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param min_len: The min mapper word length in this op, words
            will be filtered if their length is below this parameter.
        :param max_len: The max mapper word length in this op, words
            will be filtered if their length exceeds this parameter.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.min_len = min_len
        self.max_len = max_len
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def should_keep_long_word(self, word):
        if self.min_len <= len(word) <= self.max_len:
            return True
        elif self.min_len <= len(strip(word,
                                       SPECIAL_CHARACTERS)) <= self.max_len:
            return True
        else:
            return False

    def process(self, sample):
        # Track statistics
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        
        original_text = sample[self.text_key]

        sentences = split_on_newline_tab_whitespace(sample[self.text_key])
        sentences = [[[
            word for word in subsentence if self.should_keep_long_word(word)
        ] for subsentence in sentence] for sentence in sentences]
        sample[self.text_key] = merge_on_whitespace_tab_newline(sentences)
        
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
        return """Mapper to remove long words within a specific range."""

    @classmethod
    @property
    def sample(cls):
        return Sample("This paper a novel eqeqweqwewqeqwe121e1 method on LLM pretrain.", 
                      "This paper novel method LLM pretrain.")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("min_len", DataType.PositiveFloat, None, 1),
            Param("max_len", DataType.PositiveFloat, None, 9999999),
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
            self._log_line(f"[{self._name}] Long Words Removal Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with long words removed: {modified} ({modified/total*100:.2f}%)")
            self._log_line(f"Samples unchanged: {unmodified} ({unmodified/total*100:.2f}%)")
            self._log_line(f"Word length range: {self.min_len} - {self.max_len}")
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