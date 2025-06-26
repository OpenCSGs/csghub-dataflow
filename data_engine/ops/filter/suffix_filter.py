from typing import List, Tuple, Union

from data_engine.utils.constant import Fields

from ..base_op import OPERATORS, Filter, Sample, Param, DataType


@OPERATORS.register_module('suffix_filter')
class SuffixFilter(Filter):
    """Filter to keep samples with specified suffix."""

    def __init__(self,
                 suffixes: Union[str, List[str], Tuple[str]] = [],
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param suffixes: the suffix of text that will be keep.
            For example: '.txt', 'txt' or ['txt', '.pdf', 'docx']
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        if suffixes is None:
            self.suffixes = []
        elif isinstance(suffixes, str):
            self.suffixes = [suffixes]
        else:
            self.suffixes = suffixes

    def compute_stats(self, sample):
        return sample

    def process(self, sample):
        if self.suffixes:
            if sample[Fields.suffix] in self.suffixes:
                return True
            else:
                return False
        else:
            return True
    @classmethod
    @property
    def description(cls):
        return """Filter to keep samples with specified suffix."""

    @classmethod
    @property
    def sample(cls):
        return Sample("{"
            "'text': '中文也是一个字算一个长度',"
            "Fields.suffix: '.txt'"
        "}", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("suffixes", DataType.LIST, None, []),
        ]