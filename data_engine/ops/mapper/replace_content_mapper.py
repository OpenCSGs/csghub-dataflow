from typing import List, Union

import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('replace_content_mapper')
class ReplaceContentMapper(Mapper):
    """Mapper to replace all content in the text that matches
    a specific regular expression pattern with a designated
    replacement string."""

    def __init__(self,
                 pattern: Union[str, List[str]] = None,
                 repl: Union[str, List[str]] = '',
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param pattern: regular expression pattern(s) to search for within text
        :param repl: replacement string(s), default is empty string
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.pattern = pattern
        self.repl = repl
        self.compiled_patterns = []
        if isinstance(pattern, str):
            self.compiled_patterns.append(self._prepare_pattern(pattern))
        elif isinstance(pattern, list):
            for p in pattern:
                self.compiled_patterns.append(self._prepare_pattern(p))
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def _prepare_pattern(self, pattern: str) -> re.Pattern:
        """Prepare the regular expression pattern."""
        if ((pattern is not None and len(pattern) > 2)
                and (pattern.startswith("r'") and pattern.endswith("'")
                     or pattern.startswith('r"') and pattern.endswith('"'))):
            pattern = pattern[2:-1]
        return re.compile(pattern, flags=re.DOTALL)

    def process(self, sample):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        original_text = sample[self.text_key]
        
        if self.pattern is None:
            if getattr(self, 'enable_detailed_logging', False):
                self.unmodified_samples += 1
            return sample

        for i, pattern in enumerate(self.compiled_patterns):
            if isinstance(self.repl, list) and i < len(self.repl):
                replacement = self.repl[i]
            elif isinstance(self.repl, list) and i >= len(self.repl):
                raise ValueError(f"pattern length: {len(self.pattern)} '"
                                 f'must be equal to '
                                 f'repl length: {len(self.repl)}')
            else:
                replacement = self.repl

            sample[self.text_key] = pattern.sub(replacement,
                                                sample[self.text_key])

        if getattr(self, 'enable_detailed_logging', False):
            if sample[self.text_key] != original_text:
                self.modified_samples += 1
            else:
                self.unmodified_samples += 1
        return sample

    @classmethod
    @property
    def description(cls):
        return     """Mapper to replace all content in the text that matches
    a specific regular expression pattern with a designated
    replacement string."""

    @classmethod
    @property
    def sample(cls):
        return Sample("多个●■►▼这样的特殊字符可以►▼▲▴∆吗？", 
                      "多个<SPEC>►▼这样的特殊字符可以►▼▲▴∆吗？")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("pattern", DataType.LIST, None, []),
            Param("repl", DataType.LIST, None, [])
        ]
    
    def run(self, dataset, *, exporter=None, tracer=None):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples = 0
            self.modified_samples = 0
            self.unmodified_samples = 0
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        return result
    
    def _log_mapper_summary(self):
        try:
            from loguru import logger
            total, modified, unmodified = self.total_samples, self.modified_samples, self.unmodified_samples
            if total == 0: return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Replace Content Summary")
            self._log_line("="*60)
            self._log_line(f"Total: {total}, Replaced: {modified} ({modified/total*100:.2f}%), Unchanged: {unmodified} ({unmodified/total*100:.2f}%)")
            self._log_line("="*60)
        except: pass
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)