from jsonargparse.typing import List

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType
from ..common import (SPECIAL_CHARACTERS, get_words_from_document,
                      merge_on_whitespace_tab_newline,
                      split_on_newline_tab_whitespace, strip)

OP_NAME = 'remove_words_with_incorrect_substrings_mapper'

with AvailabilityChecking(['sentencepiece'], OP_NAME):
    import sentencepiece  # noqa: F401


@OPERATORS.register_module(OP_NAME)
class RemoveWordsWithIncorrectSubstringsMapper(Mapper):
    """Mapper to remove words with incorrect substrings."""

    def __init__(self,
                 lang: str = 'en',
                 tokenization: bool = False,
                 substrings: List = None,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param lang: sample in which language
        :param tokenization: whether to use model to tokenize documents
        :param substrings: The incorrect substrings in words.
        :param args: extra args
        :param kwargs: extra args
        """
        if substrings is None:
            substrings = ['http', 'www', '.com', 'href', '//']
        super().__init__(*args, **kwargs)
        self.tokenization = tokenization
        self.substrings = substrings
        self.lang = lang
        if tokenization:
            self.model_key = prepare_model(model_type='sentencepiece',
                                           lang=lang)
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def should_keep_word_with_incorrect_substrings(self, word, substrings):
        word = strip(word, SPECIAL_CHARACTERS)
        should_keep = all([(i_substr not in word) for i_substr in substrings])
        return should_keep

    def process(self, sample):
        # Track statistics
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        
        original_text = sample[self.text_key]
        
        if self.tokenization:
            tokenizer = get_model(self.model_key)
            sentences = get_words_from_document(
                sample[self.text_key],
                token_func=tokenizer.encode_as_pieces if tokenizer else None)
            words = [
                word.replace('▁', '') for word in sentences
                if self.should_keep_word_with_incorrect_substrings(
                    word.replace('▁', ''), self.substrings)
            ]
            if len(words) != len(sentences):
                sample[self.text_key] = ''.join(words)
        else:
            sentences = split_on_newline_tab_whitespace(sample[self.text_key])
            sentences = [[[
                word for word in subsentence
                if self.should_keep_word_with_incorrect_substrings(
                    word, self.substrings)
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
        return """Mapper to remove words with incorrect substrings."""

    @classmethod
    @property
    def sample(cls):
        return Sample("请用百度www.baidu.com进行搜索", 
                      "请用百度www.baidu进行搜索")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("lang", DataType.STRING, {
                "en": "en",
                "zh": "zh",
            }, "en"),
            Param("tokenization", DataType.BOOLEAN, None, False),
            Param("substrings", DataType.LIST, None, ['http', 'www', '.com', 'href', '//']),
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
            total = self.total_samples
            modified = self.modified_samples
            unmodified = self.unmodified_samples
            if total == 0:
                return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Incorrect Substrings Removal Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with incorrect substrings removed: {modified} ({modified/total*100:.2f}%)")
            self._log_line(f"Samples unchanged: {unmodified} ({unmodified/total*100:.2f}%)")
            self._log_line("="*60)
        except Exception as e:
            import traceback
            from loguru import logger
            logger.error(f"Failed to generate mapper logging: {e}\n{traceback.format_exc()}")
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)