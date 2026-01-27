# Some code here has been modified from:
# https://huggingface.co/spaces/huggingface/text-data-filtering
# --------------------------------------------------------

from jsonargparse.typing import ClosedUnitInterval

from data_engine.utils.constant import Fields, StatsKeys

from ..base_op import OPERATORS, Filter, Sample, Param, DataType
from ..common import SPECIAL_CHARACTERS


@OPERATORS.register_module('special_characters_filter')
class SpecialCharactersFilter(Filter):
    """Filter to keep samples with special-char ratio within a specific
    range."""

    def __init__(self,
                 min_ratio: ClosedUnitInterval = 0.0,
                 max_ratio: ClosedUnitInterval = 0.25,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param min_ratio: The min filter ratio in this op, samples will
            be filtered if their special-char ratio is below this
            parameter.
        :param max_ratio: The max filter ratio in this op, samples will
            be filtered if their special-char ratio exceeds this
            parameter.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

    def compute_stats(self, sample):
        # check if it's computed already
        if StatsKeys.special_char_ratio in sample[Fields.stats]:
            return sample

        text = sample[self.text_key]
        text_len = len(text)
        special_char_count = len([c for c in text if c in SPECIAL_CHARACTERS])
        ratio = (special_char_count / text_len) if text_len != 0 else 0.0
        
        # get ratio of special characters
        sample[Fields.stats][StatsKeys.special_char_ratio] = ratio
        
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
        sample[Fields.stats][f'{StatsKeys.special_char_ratio}_detail'] = {
            'ratio': str(ratio),
            'special_char_count': special_char_count,
            'text_length': text_len,
            'keep': keep,
            'reason': reason
        }
        
        return sample

    def process(self, sample):
        if self.min_ratio <= \
                sample[Fields.stats][StatsKeys.special_char_ratio] \
                <= self.max_ratio:
            return True
        else:
            return False

    @classmethod
    @property
    def description(cls):
        return """Filter to keep samples with special-char ratio within a specific
    range."""

    @classmethod
    @property
    def sample(cls):
        return Sample("emoji表情测试下😊，😸31231", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("min_ratio", DataType.ClosedUnitInterval, None, 0.0),
            Param("max_ratio", DataType.ClosedUnitInterval, None, 0.25),
        ]