from ..base_op import OPERATORS, Filter, Sample, Param, DataType
from ...utils.constant import Fields, StatsKeys

OP_NAME = 'text_high_score_filter'


@OPERATORS.register_module('text_high_score_filter')
class TextHighScoreFilter(Filter):

    def __init__(self,
                 score_field: str = 'score',
                 min_score: float = 0.6,
                 max_score: float = 2.0,
                 *args,
                 **kwarg):
        super().__init__(*args, **kwarg)
        self.score_field = score_field
        self.min_score = min_score
        self.max_score = max_score

    def compute_stats(self, sample, context=False):
        if StatsKeys.high_score in sample[Fields.stats]:
            return sample

        score = sample[self.score_field]
        stats = (self.min_score <= score < self.max_score) if isinstance(score, (int, float)) else False

        sample[Fields.stats][StatsKeys.high_score] = stats
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
            Param("score_field", DataType.STRING, {}, 'score'),
            Param("min_score", DataType.FLOAT, {}, 0.6),
            Param("max_score", DataType.FLOAT, {}, 2.0),
        ]
