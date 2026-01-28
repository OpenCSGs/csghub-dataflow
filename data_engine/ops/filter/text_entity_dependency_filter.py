import json

import numpy as np
from loguru import logger
from openai import OpenAI

from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.mm_utils import remove_special_tokens

from ..base_op import OPERATORS, Filter, Sample, Param, DataType

OP_NAME = 'text_entity_dependency_filter'

DEFAULT_SYSTEM_PROMPT = '''你是一个专业的语言学分析助手。你的任务是分析文本中的实体（名词、专有名词、代词）及其依存关系。

规则：
1. 识别文本中所有实体（名词、专有名词、代词）
2. 对每个实体，统计它在句子中与其他词的语法关联数量（依存边数）
   - 依存边包括：主谓关系、动宾关系、定中关系、介宾关系等
   - 孤立的实体（如独立成句的词）依存边数为 0
3. 只返回 JSON 格式：{"dependency_edges": [数字列表]}
4. 如果没有识别到实体，返回：{"dependency_edges": []}
5. 不要添加任何解释或其他内容

示例：
输入："小明在北京工作"
输出：{"dependency_edges": [1, 1]}
（实体：小明-主语关系1条边，北京-介宾关系1条边）

输入："苹果。香蕉。"
输出：{"dependency_edges": [0, 0]}
（实体：苹果、香蕉各独立成句，无依存关系）

输入："上上下下左左右右"
输出：{"dependency_edges": []}
（无名词/代词类实体）'''


@OPERATORS.register_module(OP_NAME)
class TextEntityDependencyFilter(Filter):
    """
    Identify the entities in the text which are independent with other token,
    and filter them. The text containing no entities will be omitted.
    Uses remote LLM API to detect entity dependencies.
    """

    _accelerator = 'cpu'

    def __init__(self,
                 base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                 model: str = 'qwen-max',
                 api_key: str = '',
                 min_dependency_num: int = 1,
                 any_or_all: str = 'all',
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param base_url: API base URL for LLM service. Default is Alibaba DashScope.
        :param model: Model name to use. Default is qwen-max.
        :param api_key: API key for authentication. Required.
        :param min_dependency_num: The min dependency edge number in the filtering.
            Entities are considered independent if their number of edges in the
            dependency tree is below this parameter.
        :param any_or_all: keep this sample with 'any' or 'all' strategy.
            'any': keep this sample if any entity is dependent.
            'all': keep this sample only if all entities are dependent.
        """
        super().__init__(*args, **kwargs)
        self.num_proc = 1

        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.min_dependency_num = min_dependency_num

        if any_or_all not in ['any', 'all']:
            raise ValueError(f'Keep strategy [{any_or_all}] is not supported. '
                             f'Can only be one of ["any", "all"].')
        self.any = (any_or_all == 'any')

        if not self.api_key:
            raise ValueError("api_key is required")

        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def compute_stats(self, sample, context=False):
        # check if it's computed already
        if StatsKeys.num_dependency_edges in sample[Fields.stats]:
            return sample

        text = remove_special_tokens(sample[self.text_key])

        # Call LLM API to analyze entity dependencies
        dependency_edges = self._analyze_dependency_with_llm(text)
        sample[Fields.stats][StatsKeys.num_dependency_edges] = dependency_edges

        # Determine filter result and reason for detailed logging
        keep_bools = np.array([
            self.min_dependency_num <= num_edge
            for num_edge in dependency_edges
        ])

        # omit the samples without entity
        if len(keep_bools) <= 0:
            keep = False
            reason = 'no_entities'
        else:
            # different strategies
            if self.any:
                keep = keep_bools.any()
            else:
                keep = keep_bools.all()
            reason = 'kept' if keep else 'dependency_too_low'

        # Store detailed information for logging
        sample[Fields.stats][f'{StatsKeys.num_dependency_edges}_detail'] = {
            'num_entities': len(dependency_edges),
            'dependency_edges': str(dependency_edges),
            'keep': keep,
            'reason': reason,
            'strategy': 'any' if self.any else 'all'
        }

        return sample

    def _analyze_dependency_with_llm(self, text: str) -> list:
        """
        Use LLM to analyze entity dependencies in text.

        :param text: Input text to analyze.
        :return: List of dependency edge counts for each entity.
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
            dependency_edges = result.get('dependency_edges', [])
            # Ensure all values are integers
            return [int(x) for x in dependency_edges]

        except json.JSONDecodeError as e:
            logger.error(f'[{OP_NAME}] JSON parsing error: {e}, response: {response_text}')
            return []
        except Exception as e:
            logger.error(f'[{OP_NAME}] LLM API call failed: {e}')
            return []

    def process(self, sample):
        num_dependency_edges = sample[Fields.stats][
            StatsKeys.num_dependency_edges]
        keep_bools = np.array([
            self.min_dependency_num <= num_edge
            for num_edge in num_dependency_edges
        ])
        # omit the samples without entity
        if len(keep_bools) <= 0:
            return False

        # different strategies
        if self.any:
            return keep_bools.any()
        else:
            return keep_bools.all()

    @classmethod
    @property
    def description(cls):
        return """实体依存过滤算子：使用远程 LLM 分析文本中实体的依存关系，过滤掉实体缺乏语法关联的样本。"""

    @classmethod
    @property
    def sample(cls):
        return Sample("小明在北京的公司工作", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("base_url", DataType.STRING, None, "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            Param("model", DataType.STRING, None, "qwen-max"),
            Param("api_key", DataType.STRING, None, ""),
            Param("min_dependency_num", DataType.INTEGER, None, 1),
            Param("any_or_all", DataType.STRING, {
                "all": "all",
                "any": "any",
            }, "all"),
        ]
