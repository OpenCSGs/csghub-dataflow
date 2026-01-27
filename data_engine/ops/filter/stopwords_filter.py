# Some code here has been modified from:
# https://huggingface.co/spaces/huggingface/text-data-filtering
# --------------------------------------------------------

from jsonargparse.typing import ClosedUnitInterval, List

from data_engine.utils.asset_utils import ASSET_DIR, load_words_asset
from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.constant import Fields, InterVars, StatsKeys
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Filter, Sample, Param, DataType
from ..common import (SPECIAL_CHARACTERS, get_words_from_document,
                      words_refinement)
from ..op_fusion import INTER_WORDS

OP_NAME = 'stopwords_filter'

with AvailabilityChecking(['sentencepiece'], OP_NAME):
    import sentencepiece  # noqa: F401


@OPERATORS.register_module(OP_NAME)
@INTER_WORDS.register_module(OP_NAME)
class StopWordsFilter(Filter):
    """Filter to keep samples with stopword ratio larger than a specific min
    value."""

    def __init__(self,
                 lang: str = 'en',
                 tokenization: bool = False,
                 min_ratio: ClosedUnitInterval = 0.3,
                 stopwords_dir: str = ASSET_DIR,
                 use_words_aug: bool = False,
                 words_aug_group_sizes: List = [2],
                 words_aug_join_char: str = '',
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param lang: Consider stopwords in what language. If lang ==
            "all", we will adopt the one merged from all the available
            languages
        :param tokenization: whether to use model to tokenize documents
        :param min_ratio: The min filter ratio in this op.
        :param stopwords_dir: The directory storing the stopwords
            file(s) whose name includes "stopwords" and in json format
        :param use_words_aug: Whether to augment words, especially for
            Chinese and Vietnamese
        :param words_aug_group_sizes: The group size of words to augment
        :param words_aug_join_char: The join char between words to
            augment
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.lang = lang
        self.min_ratio = min_ratio
        self.use_words_aug = use_words_aug
        self.words_aug_group_sizes = words_aug_group_sizes
        self.words_aug_join_char = words_aug_join_char
        self.model_key = None
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

        self.STOPWORDS = load_words_asset(words_dir=stopwords_dir,
                                          words_type='stopwords')
        if 'all' not in self.STOPWORDS:
            self.STOPWORDS['all'] = [
                val for vals in self.STOPWORDS.values() for val in vals
            ]
        if tokenization:
            self.model_key = prepare_model(model_type='sentencepiece',
                                           lang=lang)

    def compute_stats(self, sample, context=False):
        # check if it's computed already
        if StatsKeys.stopwords_ratio in sample[Fields.stats]:
            return sample

        # try to get words from context
        words_key = f'{InterVars.words}-{self.model_key}'
        if context and words_key in sample[Fields.context]:
            words = sample[Fields.context][words_key]
        else:
            tokenizer = get_model(self.model_key)
            words = get_words_from_document(
                sample[self.text_key],
                token_func=tokenizer.encode_as_pieces if tokenizer else None)
            if context:
                sample[Fields.context][words_key] = words

        # try to get refined words from context
        refined_words_key = f'{InterVars.refined_words}-True-SPECIAL_CHARS-' \
                            f'{self.use_words_aug}-' \
                            f'{self.words_aug_group_sizes}-' \
                            f'{self.words_aug_join_char}'
        if context and refined_words_key in sample[Fields.context]:
            words = sample[Fields.context][refined_words_key]
        else:
            words = words_refinement(
                words,
                lower_case=True,
                strip_chars=SPECIAL_CHARACTERS,
                use_words_aug=self.use_words_aug,
                words_aug_group_sizes=self.words_aug_group_sizes,
                words_aug_join_char=self.words_aug_join_char)
            if context:
                sample[Fields.context][refined_words_key] = words

        stopwords_ratio = (
                len([word for word in words
                     if word in self.STOPWORDS[self.lang]])
                / len(words)) \
            if len(words) != 0 else 0.0

        if stopwords_ratio > 1.0:
            stopwords_ratio = 1.0

        sample[Fields.stats][StatsKeys.stopwords_ratio] = stopwords_ratio
        
        # Determine filter result and reason for detailed logging
        if stopwords_ratio >= self.min_ratio:
            keep = True
            reason = 'kept'
        else:
            keep = False
            reason = 'below_min'
        
        # Store detailed information for logging
        sample[Fields.stats][f'{StatsKeys.stopwords_ratio}_detail'] = {
            'ratio': str(stopwords_ratio),
            'keep': keep,
            'reason': reason,
            'num_words': len(words),
            'stopwords_count': len([word for word in words if word in self.STOPWORDS[self.lang]])
        }
        
        return sample

    def process(self, sample):
        return sample[Fields.stats][
            StatsKeys.stopwords_ratio] >= self.min_ratio

    @classmethod
    @property
    def description(cls):
        return """Filter to keep samples with stopword ratio larger than a specific min
    value."""

    @classmethod
    @property
    def sample(cls):
        return Sample("?", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("lang", DataType.STRING, {
                "en": "en",
                "zh": "zh",
            }, "zh"),
            Param("tokenization", DataType.BOOLEAN, None, False),
            Param("min_ratio", DataType.ClosedUnitInterval, None, 0.3),
            Param("use_words_aug", DataType.BOOLEAN, None, False),
        ]