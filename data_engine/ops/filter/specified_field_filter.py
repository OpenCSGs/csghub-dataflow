from typing import List, Tuple, Union

from ..base_op import OPERATORS, Filter, Sample, Param, DataType


@OPERATORS.register_module('specified_field_filter')
class SpecifiedFieldFilter(Filter):
    """
    Filter based on specified field information.

    If the specified field information in the sample is not within the
    specified target value, the sample will be filtered.
    """

    def __init__(self,
                 field_key: str = '',
                 target_value: Union[List, Tuple] = [],
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param field_key: Filter based on the specified value
            corresponding to the target key. The target key
            corresponding to multi-level field information need to be
            separated by '.'.
        :param target_value: The range of specified field information
            corresponding to the samples that need to be retained.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.field_key = field_key
        self.target_value = target_value

    def compute_stats(self, sample):
        return sample

    def process(self, sample):
        if not (self.field_key and self.target_value):
            return True

        field_value = sample
        for key in self.field_key.split('.'):
            assert key in field_value.keys(), "'{}' not in {}".format(
                key, field_value.keys())
            field_value = field_value[key]

        if not (isinstance(field_value, list)
                or isinstance(field_value, tuple)):
            field_value = [field_value]
        for value in field_value:
            if value not in self.target_value:
                return False
        return True

    @classmethod
    @property
    def description(cls):
        return """
    Filter based on specified field information.

    If the specified field information in the sample is not within the
    specified target value, the sample will be filtered.
    """

    @classmethod
    @property
    def sample(cls):
        return Sample("{"
            "'text': '中文也是一个字算一个长度',"
            "'meta': {"
            "    'suffix': '.txt',"
            "    'star': 100"
            "}"
        "}", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("field_key", DataType.STRING, None, ''),
            Param("target_value", DataType.LIST, None, []),
        ]