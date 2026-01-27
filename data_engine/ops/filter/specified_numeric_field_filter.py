import sys

from ..base_op import OPERATORS, Filter, Sample, Param, DataType


def is_number(s):
    if s:
        try:
            float(s)
            return True
        except ValueError:
            pass
    return False


@OPERATORS.register_module('specified_numeric_field_filter')
class SpecifiedNumericFieldFilter(Filter):
    """
    Filter based on specified numeric field information.

    If the specified numeric information in the sample is not within the
    specified range, the sample will be filtered.
    """

    def __init__(self,
                 field_key: str = '',
                 min_value: float = -sys.maxsize,
                 max_value: float = sys.maxsize,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param field_key: Filter based on the specified numeric value
            corresponding to the target key. The target key
            corresponding to multi-level field information need to be
            separated by '.'.
        :param min_value: The min filter value in SpecifiedNumericField
            op, samples will be filtered if their specified numeric
            field value is below this parameter.
        :param max_value: The max filter value in SpecifiedNumericField
            op, samples will be filtered if their specified numeric
            field value exceeds this parameter.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.field_key = field_key
        self.min_value = min_value
        self.max_value = max_value
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

    def compute_stats(self, sample):
        # specified_numeric_field_filter doesn't compute stats, but we add detail for logging
        if not self.field_key:
            keep = True
            reason = 'kept'
            field_value = 'N/A'
        else:
            try:
                field_value = sample
                for key in self.field_key.split('.'):
                    field_value = field_value[key]
                
                if is_number(field_value):
                    field_value_float = float(field_value)
                    if field_value_float < self.min_value:
                        keep = False
                        reason = 'below_min'
                    elif field_value_float > self.max_value:
                        keep = False
                        reason = 'above_max'
                    else:
                        keep = True
                        reason = 'kept'
                else:
                    keep = False
                    reason = 'not_numeric'
            except (KeyError, AssertionError) as e:
                keep = False
                reason = 'field_not_found'
                field_value = 'N/A'
        
        # Store detailed information for logging
        sample['__dj__stats__']['specified_numeric_field_filter_detail'] = {
            'field_key': self.field_key,
            'field_value': str(field_value),
            'min_value': self.min_value,
            'max_value': self.max_value,
            'keep': keep,
            'reason': reason
        }
        
        return sample

    def process(self, sample):
        if not self.field_key:
            return True

        field_value = sample
        for key in self.field_key.split('.'):
            assert key in field_value.keys(), "'{}' not in {}".format(
                key, field_value.keys())
            field_value = field_value[key]

        if is_number(field_value):
            field_value = float(field_value)
            return self.min_value <= field_value <= self.max_value
        else:
            return False

    @classmethod
    @property
    def description(cls):
        return """
    Filter based on specified numeric field information.

    If the specified numeric information in the sample is not within the
    specified range, the sample will be filtered.
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
            Param("min_value", DataType.FLOAT, None, -999999),
            Param("max_value", DataType.FLOAT, None, 999999),
        ]
    
