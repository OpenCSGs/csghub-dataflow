import json

from loguru import logger
from openai import OpenAI

from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.mm_utils import remove_special_tokens

from ..base_op import OPERATORS, Filter, Sample, Param, DataType

OP_NAME = 'text_action_filter'

DEFAULT_SYSTEM_PROMPT = '''你是一个专业的文本分析助手。你的任务是统计文本中的动作词（动词）数量。

规则：
1. 识别文本中所有表示动作的动词
2. 只统计实际动作词，不包括助动词、情态动词
3. 只返回 JSON 格式：{"num_action": 数字}
4. 不要添加任何解释或其他内容

示例：
输入："我今天去公园跑步，然后回家吃饭。"
输出：{"num_action": 4}
（动作词：去、跑步、回、吃饭）'''


@OPERATORS.register_module(OP_NAME)
class TextActionFilter(Filter):
    """
    Filter to keep texts those contain actions in the text.
    Uses remote LLM API to detect actions.
    """

    _accelerator = 'cpu'

    def __init__(self,
                 base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                 model: str = 'qwen-max',
                 api_key: str = '',
                 min_action_num: int = 1,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param base_url: API base URL for LLM service. Default is Alibaba DashScope.
        :param model: Model name to use. Default is qwen-max.
        :param api_key: API key for authentication. Required.
        :param min_action_num: The minimum action number in the filtering. Samples
            will be filtered if their action number in the text is below this
            parameter.
        """
        super().__init__(*args, **kwargs)
        self.num_proc = 1

        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.min_action_num = min_action_num

        if not self.api_key:
            raise ValueError("api_key is required")

        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def compute_stats(self, sample, context=False):
        # check if it's computed already
        if StatsKeys.num_action in sample[Fields.stats]:
            return sample

        text = remove_special_tokens(sample[self.text_key])

        # Call LLM API to count actions
        num_action = self._count_actions_with_llm(text)
        sample[Fields.stats][StatsKeys.num_action] = num_action

        # Determine filter result and reason for detailed logging
        if num_action >= self.min_action_num:
            keep = True
            reason = 'kept'
        else:
            keep = False
            reason = 'below_min'

        # Store detailed information for logging
        sample[Fields.stats][f'{StatsKeys.num_action}_detail'] = {
            'num_action': num_action,
            'keep': keep,
            'reason': reason
        }

        return sample

    def _count_actions_with_llm(self, text: str) -> int:
        """
        Use LLM to count the number of actions in text.

        :param text: Input text to analyze.
        :return: Number of actions detected.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                stream=False
            )

            response_text = completion.choices[0].message.content.strip()

            # Parse JSON response
            result = json.loads(response_text)
            num_action = int(result.get('num_action', 0))
            return num_action

        except json.JSONDecodeError as e:
            logger.error(f'[{OP_NAME}] JSON parsing error: {e}, response: {response_text}')
            return 0
        except Exception as e:
            logger.error(f'[{OP_NAME}] LLM API call failed: {e}')
            return 0

    def process(self, sample):
        num_action = sample[Fields.stats][StatsKeys.num_action]
        return self.min_action_num <= num_action

    @classmethod
    @property
    def description(cls):
        return """动作过滤算子：使用远程 LLM 检测文本中的动作词数量，过滤动作数量不足的样本。"""

    @classmethod
    @property
    def sample(cls):
        return Sample("我今天去公园跑步，然后回家吃饭。", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("base_url", DataType.STRING, None, "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            Param("model", DataType.STRING, None, "qwen-max"),
            Param("api_key", DataType.STRING, None, ""),
            Param("min_action_num", DataType.INTEGER, None, 1),
        ]
