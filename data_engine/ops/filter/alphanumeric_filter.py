import sys

from jsonargparse.typing import PositiveFloat

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Filter, Sample, Param, DataType
from ..common import get_words_from_document

OP_NAME = 'alphanumeric_filter'

with AvailabilityChecking(['transformers'], OP_NAME):
    import transformers  # noqa: F401


@OPERATORS.register_module('alphanumeric_filter')
class AlphanumericFilter(Filter):
    """Filter to keep samples with alphabet/numeric ratio within a specific
    range."""

    def __init__(self,
                 tokenization: bool = False,
                 min_ratio: float = 0.25,
                 max_ratio: PositiveFloat = sys.maxsize,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param tokenization: Whether to count the ratio of alphanumeric
            to the total number of tokens. if tokenization=False, it
            will count the ratio of alphanumeric to the total number of
            characters.
        :param min_ratio: The min filter ratio in alphanumeric op,
            samples will be filtered if their alphabet/numeric ratio is
            below this parameter.
        :param max_ratio: The max filter ratio in alphanumeric op,
            samples will be filtered if their alphabet/numeric ratio
            exceeds this parameter.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.tokenization = tokenization
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.model_key = None
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

        if tokenization:
            self.model_key = prepare_model(
                model_type='huggingface',
                pretrained_model_name_or_path='EleutherAI/pythia-6.9b-deduped',
                return_model=False)

    def compute_stats(self, sample):
        if self.tokenization:
            if StatsKeys.alpha_token_ratio in sample[Fields.stats]:
                return sample
            alpha_count = sum(
                map(lambda char: 1
                    if char.isalpha() else 0, sample[self.text_key]))
            tokenizer = get_model(self.model_key)
            token_count = len(
                get_words_from_document(
                    sample[self.text_key],
                    token_func=tokenizer.tokenize if tokenizer else None))
            ratio = (alpha_count / token_count) if token_count != 0 else 0.0
            sample[Fields.stats][StatsKeys.alpha_token_ratio] = ratio
            
            # Determine filter result and reason for detailed logging
            if ratio < self.min_ratio:
                keep = False
                reason = 'below_min'
            elif ratio > self.max_ratio:
                keep = False
                reason = 'above_max'
            else:
                keep = True
                reason = 'kept'
            
            # Store detailed information for logging
            sample[Fields.stats][f'{StatsKeys.alpha_token_ratio}_detail'] = {
                'ratio': str(ratio),
                'keep': keep,
                'reason': reason,
                'alpha_count': alpha_count,
                'token_count': token_count
            }
        else:
            if StatsKeys.alnum_ratio in sample[Fields.stats]:
                return sample
            text = sample[self.text_key]
            text_len = len(text)
            alnum_count = sum(
                map(lambda char: 1
                    if char.isalnum() else 0, text))
            ratio = (alnum_count / text_len) if text_len != 0 else 0.0
            sample[Fields.stats][StatsKeys.alnum_ratio] = ratio
            
            # Determine filter result and reason for detailed logging
            if ratio < self.min_ratio:
                keep = False
                reason = 'below_min'
            elif ratio > self.max_ratio:
                keep = False
                reason = 'above_max'
            else:
                keep = True
                reason = 'kept'
            
            # Store detailed information for logging
            sample[Fields.stats][f'{StatsKeys.alnum_ratio}_detail'] = {
                'ratio': str(ratio),
                'keep': keep,
                'reason': reason,
                'alnum_count': alnum_count,
                'text_length': text_len
            }
        return sample

    def process(self, sample):
        ratio = sample[Fields.stats][
            StatsKeys.alpha_token_ratio] if self.tokenization else sample[
                Fields.stats][StatsKeys.alnum_ratio]
        if self.min_ratio <= ratio <= self.max_ratio:
            return True
        else:
            return False

    @classmethod
    @property
    def description(cls):
        return """Filter to keep samples with alphabet/numeric ratio within a specific
    range."""

    @classmethod
    @property
    def sample(cls):
        return Sample("emoji表情测试下😊，😸31231\n", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("tokenization", DataType.BOOLEAN, None, False),
            Param("min_ratio", DataType.FLOAT, None, 0.25),
            Param("max_ratio", DataType.PositiveFloat, None, 999999),
        ]