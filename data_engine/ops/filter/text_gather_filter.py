# Some code here has been modified from:
# https://github.com/yuyijiong/fineweb-edu-chinese/
# --------------------------------------------------------

from data_engine.ops.base_op import OPERATORS, Filter, Sample
from data_engine.utils.constant import Fields


@OPERATORS.register_module('gather_generated_data')
class TextGatherFilter(Filter):
    """
    Identify the entities in the text which are independent with other token,
    and filter them. The text containing no entities will be omitted.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialization method.

        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.is_drop = False
        self.hash_set = set()

    def compute_stats(self, sample, context=False):
        # Return early if conversation already exists
        if "conversation" in sample:
            return sample

        # Clean prompt and answer fields
        sample['first_prompt'] = sample['instruction'].replace("||", "").replace("<|im_end|>", "").strip()
        sample['first_prompt'] = None if len(sample['first_prompt']) < 3 else sample['first_prompt']

        sample['first_answer'] = sample['response'].replace("||", "").replace("<|im_end|>", "").strip()
        sample['first_answer'] = None if len(sample['first_answer']) < 3 else sample['first_answer']

        # Build conversation format
        if not sample['first_prompt'] or not sample['first_answer']:
            sample['conversation'] = None
        else:
            sample['conversation'] = [
                {"role": "user", "content": sample["first_prompt"]},
                {"role": "assistant", "content": sample["first_answer"]}
            ]

        # Check for duplicates
        is_duplicate = sample['first_prompt'] in self.hash_set
        self.hash_set.add(sample['first_prompt'])

        # Set drop flag
        sample[Fields.stats]['is_drop'] = is_duplicate or not sample['conversation']
        self.is_drop = sample[Fields.stats]['is_drop']

        return sample

    def process(self, sample):
        if self.is_drop:
            return not sample[Fields.stats]['is_drop']
        else:
            return False

    @classmethod
    @property
    def description(cls):
        return """Filter for collecting and processing generated data."""

    @classmethod
    @property
    def sample(cls):
        return Sample("基于前一步结果，除掉 || 与 <|im_end|> 字符并且过滤 出 content 为空的数据 ", "")

    @classmethod
    @property
    def init_params(cls):
        return None
