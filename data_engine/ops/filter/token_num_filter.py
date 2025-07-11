import sys

from jsonargparse.typing import PositiveInt

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Filter, Sample, Param, DataType
from ..common import get_words_from_document

OP_NAME = 'token_num_filter'

with AvailabilityChecking(['transformers'], OP_NAME):
    import transformers  # noqa: F401


@OPERATORS.register_module(OP_NAME)
class TokenNumFilter(Filter):
    """Filter to keep samples with total token number within a specific
    range."""

    def __init__(self,
                 hf_tokenizer: str = 'EleutherAI/pythia-6.9b-deduped',
                 min_num: PositiveInt = 10,
                 max_num: PositiveInt = sys.maxsize,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param hf_tokenizer: the tokenizer name of Hugging Face tokenizers.
        :param min_num: The min filter token number in this op, samples
            will be filtered if their token number is below this
            parameter.
        :param max_num: The max filter token number in this op, samples
            will be filtered if their token number exceeds this
            parameter.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.min_num = min_num
        self.max_num = max_num
        self.hf_tokenizer = hf_tokenizer
        self.model_key = prepare_model(
            model_type='huggingface',
            pretrained_model_name_or_path=hf_tokenizer,
            return_model=False)

    def compute_stats(self, sample):
        # check if it's computed already
        if StatsKeys.num_token in sample[Fields.stats]:
            return sample

        tokenizer = get_model(self.model_key)
        tokens = get_words_from_document(
            sample[self.text_key],
            token_func=tokenizer.tokenize if tokenizer else None)
        sample[Fields.stats][StatsKeys.num_token] = len(tokens)
        return sample

    def process(self, sample):
        if self.min_num <= sample[Fields.stats][
                StatsKeys.num_token] <= self.max_num:
            return True
        else:
            return False

    @classmethod
    @property
    def description(cls):
        return """Filter to keep samples with total token number within a specific
    range."""

    @classmethod
    @property
    def sample(cls):
        return Sample("Today is Sund Sund Sund Sund Sund Sunda and it's a happy day!", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("hf_tokenizer", DataType.STRING, {
                "EleutherAI/pythia-6.9b-deduped": "EleutherAI/pythia-6.9b-deduped"
            }, "EleutherAI/pythia-6.9b-deduped"),
            Param("min_num", DataType.PositiveFloat, None, 10),
            Param("max_num", DataType.PositiveFloat, None, 999999),
        ]