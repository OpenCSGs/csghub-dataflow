# Some code here has been modified from:
# https://huggingface.co/spaces/huggingface/text-data-filtering
# --------------------------------------------------------
# Modified to use LLM API for text quality evaluation

import json

from jsonargparse.typing import PositiveFloat
from loguru import logger
from openai import OpenAI

from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.mm_utils import remove_special_tokens

from ..base_op import OPERATORS, Filter, Sample, Param, DataType

OP_NAME = 'perplexity_filter'

DEFAULT_SYSTEM_PROMPT = '''你是一个专业的文本质量评估助手。请评估文本的语言质量，返回一个困惑度分数。

评分标准（分数越低表示质量越好）：
- 0-100：语法正确、表达流畅、内容有意义（优质文本）
- 100-500：基本通顺，有少量语法或表达问题
- 500-1000：存在明显语法错误或表达不清晰
- 1000-1500：难以理解，存在大量错误
- 1500以上：乱码、无意义重复、完全不可读

只返回 JSON 格式：{"perplexity": 数字}
不要添加任何解释或其他内容。

示例：
输入："人工智能正在改变我们的生活方式。"
输出：{"perplexity": 50}

输入："的的的的的的的的"
输出：{"perplexity": 2000}'''


@OPERATORS.register_module(OP_NAME)
class PerplexityFilter(Filter):
    """Filter to keep samples with perplexity score less than a specific max
    value. Uses LLM API to evaluate text quality."""

    _accelerator = 'cpu'

    def __init__(self,
                 base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                 model: str = 'qwen-max',
                 api_key: str = '',
                 max_ppl: PositiveFloat = 1500,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param base_url: API base URL for LLM service. Default is Alibaba DashScope.
        :param model: Model name to use. Default is qwen-max.
        :param api_key: API key for authentication. Required.
        :param max_ppl: The max filter perplexity in this op, samples
            will be filtered if their perplexity exceeds this parameter.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.num_proc = 1

        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.max_ppl = max_ppl

        if not self.api_key:
            raise ValueError("api_key is required")

        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def compute_stats(self, sample, context=False):
        # check if it's computed already
        if StatsKeys.perplexity in sample[Fields.stats]:
            logger.debug(f'[{OP_NAME}] Perplexity already computed, skipping')
            return sample

        text = remove_special_tokens(sample[self.text_key])
        logger.debug(f'[{OP_NAME}] Input text (first 100 chars): {text[:100]}...')

        # Call LLM API to evaluate perplexity
        ppl = self._evaluate_perplexity_with_llm(text)
        sample[Fields.stats][StatsKeys.perplexity] = ppl
        logger.debug(f'[{OP_NAME}] Computed perplexity: {ppl}')

        # Determine filter result and reason for detailed logging
        if ppl <= self.max_ppl:
            keep = True
            reason = 'kept'
        else:
            keep = False
            reason = 'above_max'

        # Store detailed information for logging
        sample[Fields.stats][f'{StatsKeys.perplexity}_detail'] = {
            'perplexity': str(ppl),
            'keep': keep,
            'reason': reason,
            'num_chars': len(text)
        }

        return sample

    def _evaluate_perplexity_with_llm(self, text: str) -> float:
        """
        Use LLM to evaluate the perplexity score of text.
        Lower score means better quality.

        :param text: Input text to evaluate.
        :return: Perplexity score (lower is better).
        """
        try:
            logger.debug(f'[{OP_NAME}] Calling LLM API with model: {self.model}')
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                stream=False
            )

            response_text = completion.choices[0].message.content.strip()
            logger.debug(f'[{OP_NAME}] LLM raw response: {response_text}')

            # Parse JSON response
            result = json.loads(response_text)
            ppl = float(result.get('perplexity', 1500))
            logger.debug(f'[{OP_NAME}] Parsed perplexity value: {ppl}')
            return round(ppl, 1)

        except json.JSONDecodeError as e:
            logger.error(f'[{OP_NAME}] JSON parsing error: {e}, response: {response_text}')
            return 1500.0  # Return high perplexity on error (will be filtered)
        except Exception as e:
            logger.error(f'[{OP_NAME}] LLM API call failed: {e}')
            return 1500.0  # Return high perplexity on error (will be filtered)

    def process(self, sample):
        ppl = sample[Fields.stats][StatsKeys.perplexity]
        keep = ppl <= self.max_ppl
        logger.debug(f'[{OP_NAME}] Filter decision: perplexity={ppl}, max_ppl={self.max_ppl}, keep={keep}')
        return keep

    @classmethod
    @property
    def description(cls):
        return """使用 LLM 评估文本质量的过滤算子。分数越低表示质量越好，超过阈值的样本将被过滤。"""

    @classmethod
    @property
    def sample(cls):
        return Sample("Today is Sund Sund Sund Sunda and it's a happy day!\nYou know", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("base_url", DataType.STRING, None, "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            Param("model", DataType.STRING, None, "qwen-max"),
            Param("api_key", DataType.STRING, None, ""),
            Param("max_ppl", DataType.PositiveFloat, None, 1500),
        ]
