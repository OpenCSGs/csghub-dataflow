import json
import requests
from typing import Dict

from loguru import logger

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType

DEFAULT_PROMPT_TEMPLATE = """
为了输出下面代码片段，请生成对应prompt内容，该prompt应该用中文详细描述需求， 比如使用python实现什么功能。请回复：prompt=？
代码片段：
{input_data}
"""

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."

OP_NAME = 'generate_code_qa_pair_mapper'


@OPERATORS.register_module(OP_NAME)
class GenerateCodeQAPairMapper(Mapper):
    """
    Mapper to generate code QA pairs using remote LLM API.
    Supports OpenAI-compatible API formats including Qwen, DeepSeek, GPT, etc.
    """
    _accelerator = 'cpu'

    def __init__(self,
                 model_url: str = 'https://api.deepseek.com/chat/completions',
                 model_name: str = 'deepseek-chat',
                 auth_token: str = '',
                 system_prompt: str = None,
                 sampling_params: Dict = None,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param model_url: API endpoint URL (OpenAI-compatible format).
        :param model_name: Model name to use.
        :param auth_token: API authentication token.
        :param system_prompt: System prompt for the model.
        :param sampling_params: Sampling parameters for text generation.
            e.g {'temperature': 0.9, 'top_p': 0.95}
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.num_proc = 1

        self.model_url = model_url
        self.model_name = model_name
        self.auth_token = auth_token

        if not self.model_url:
            raise ValueError("model_url is required")
        if not self.auth_token:
            raise ValueError("auth_token is required")

        if system_prompt is None:
            system_prompt = DEFAULT_SYSTEM_PROMPT
        self.system_prompt = system_prompt

        if sampling_params is None:
            sampling_params = {'temperature': 0.2, 'top_k': 10, 'top_p': 0.95}
        self.sampling_params = sampling_params

    def build_prompt(self, code_snippet):
        return DEFAULT_PROMPT_TEMPLATE.format(input_data=code_snippet)

    def process(self, sample=None, rank=None):
        try:
            data = sample[self.text_key]
            input_prompt = self.build_prompt(data)

            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": input_prompt
                }
            ]

            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }

            request_data = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
            }
            # Merge sampling_params
            if self.sampling_params:
                request_data.update(self.sampling_params)

            logger.info(f'Calling API: {self.model_url}, Model: {self.model_name}')
            logger.debug(f'input_prompt is: {input_prompt}')

            response = requests.post(
                url=self.model_url,
                headers=headers,
                json=request_data,
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            
            if 'choices' not in result:
                logger.error(f'API response missing "choices" field: {result}')
                return sample
                
            response_str = result['choices'][0]['message']['content']

            logger.debug(f'response_str is: {response_str}')

            # Extract content after "prompt="
            generated_prompt = response_str.replace('prompt=', '').strip()

            message_list = {
                self.text_key: {
                    'input': generated_prompt,
                    'response': data
                }
            }

            return message_list

        except requests.exceptions.RequestException as e:
            logger.error(f'HTTP request error: {e}')
            logger.warning(f'API call failed, returning original sample')
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f'API response parsing error: {e}')
            logger.warning(f'Response parsing failed, returning original sample')
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            logger.warning(f'Exception occurred, returning original sample')

        # Return original sample on failure
        return sample

    @classmethod
    @property
    def description(cls):
        return """Code QA pair generator: Generate requirement description prompts from code snippets. Supports OpenAI-compatible APIs including Qwen, DeepSeek, GPT, etc."""

    @classmethod
    @property
    def sample(cls):
        return Sample(
            'def hello_world():\n    print("Hello, World!")\nhello_world()',
            'message:[{"input": "Write a Python function named hello_world that prints Hello, World! and call it", "response": "def hello_world():\\n    print(\\"Hello, World!\\")\\nhello_world()" }]'
        )

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("model_url", DataType.STRING, {
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions": "Qwen API",
                "https://api.deepseek.com/chat/completions": "DeepSeek API",
                "https://api.openai.com/v1/chat/completions": "OpenAI API",
            }, "https://api.deepseek.com/chat/completions"),
            Param("model_name", DataType.STRING, {
                "qwen-plus": "qwen-plus",
                "qwen-max": "qwen-max",
                "deepseek-chat": "deepseek-chat",
                "deepseek-reasoner": "deepseek-reasoner",
                "gpt-4": "gpt-4",
                "gpt-3.5-turbo": "gpt-3.5-turbo",
            }, "deepseek-chat"),
            Param("auth_token", DataType.STRING, {}, ""),
        ]
