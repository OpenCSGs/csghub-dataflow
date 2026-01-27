from ..base_op import OPERATORS, Filter, Sample, Param, DataType
from ...utils.constant import Fields, StatsKeys

OP_NAME = 'text_high_score_filter'


@OPERATORS.register_module('text_high_score_filter')
class TextHighScoreFilter(Filter):

    def __init__(self,
                 score_field: str = 'text_score',
                 min_score: float = 0.0,
                 max_score: float = 5.0,
                 *args,
                 **kwarg):
        super().__init__(*args, **kwarg)
        self.score_field = score_field
        self.min_score = min_score
        self.max_score = max_score
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

    def compute_stats(self, sample, context=False):
        if StatsKeys.high_score in sample[Fields.stats]:
            return sample

        score = sample[self.score_field]
        
        # Determine filter result and reason
        if score is None:
            # Field exists but value is null
            keep = False
            reason = 'null_value'
            score_value = 'null'
        elif not isinstance(score, (int, float)):
            # Invalid type (string, dict, list, etc.)
            keep = False
            reason = 'invalid_type'
            score_value = str(score)
        elif score < self.min_score:
            # Score below minimum threshold
            keep = False
            reason = 'below_min'
            score_value = str(score)
        elif score >= self.max_score:
            # Score at or above maximum threshold
            keep = False
            reason = 'above_max'
            score_value = str(score)
        else:
            # Score within valid range
            keep = True
            reason = 'kept'
            score_value = str(score)

        # Store result in stats
        sample[Fields.stats][StatsKeys.high_score] = keep
        
        # Store detailed information for logging (all as strings to avoid type issues)
        sample[Fields.stats][f'{StatsKeys.high_score}_detail'] = {
            'score': score_value,
            'keep': keep,
            'reason': reason
        }
        
        return sample

    def process(self, sample):
        return sample[Fields.stats][StatsKeys.high_score]

    @classmethod
    @property
    def description(cls):
        return "Filter text samples based on score value range in specified field."

    @classmethod
    @property
    def sample(cls):
        return Sample(
            before="Text dataset containing various score values, such as samples with scores 0.5, 0.7, 2.1, etc.",
            after="Only text samples with score values within the specified range are retained, "
                  "e.g., samples with scores in the [0.6, 2.0) range"
        )

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("score_field", DataType.STRING, {}, 'text_score'),
            Param("min_score", DataType.FLOAT, {}, 0),
            Param("max_score", DataType.FLOAT, {}, 5.0),
        ]
