import sys

from jsonargparse.typing import PositiveInt

from data_engine.utils.constant import Fields, StatsKeys

from ..base_op import OPERATORS, Filter, Sample, Param, DataType


@OPERATORS.register_module('text_length_filter')
class TextLengthFilter(Filter):
    """Filter to keep samples with total text length within a specific
    range."""

    def __init__(self,
                 min_len: PositiveInt = 10,
                 max_len: PositiveInt = sys.maxsize,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param min_len: The min text length in the filtering. samples
            will be filtered if their text length is below this
            parameter.
        :param max_len: The max text length in the filtering. samples
            will be filtered if their text length exceeds this
            parameter.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.min_len = min_len
        self.max_len = max_len
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

    def compute_stats(self, sample):
        # check if it's computed already
        if StatsKeys.text_len in sample[Fields.stats]:
            return sample

        text_len = len(sample[self.text_key])
        sample[Fields.stats][StatsKeys.text_len] = text_len
        
        # Determine filter result and reason for detailed logging
        if text_len < self.min_len:
            keep = False
            reason = 'below_min'
        elif text_len > self.max_len:
            keep = False
            reason = 'above_max'
        else:
            keep = True
            reason = 'kept'
        
        # Store detailed information for logging
        sample[Fields.stats][f'{StatsKeys.text_len}_detail'] = {
            'length': str(text_len),
            'keep': keep,
            'reason': reason
        }
        
        return sample

    def process(self, sample):
        if self.min_len <= sample[Fields.stats][
                StatsKeys.text_len] <= self.max_len:
            return True
        else:
            return False

    @classmethod
    @property
    def description(cls):
        return """Filter to keep samples with total text length within a specific
    range."""

    @classmethod
    @property
    def sample(cls):
        return Sample("Today is Sund Sund Sund Sund Sund Sunda and it's a happy day!", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("min_len", DataType.PositiveFloat, None, 10),
            Param("max_len", DataType.PositiveFloat, None, 999999),
        ]