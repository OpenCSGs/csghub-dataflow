import json
import re
import requests

from loguru import logger

from data_engine.ops.base_op import OPERATORS, Mapper, Sample, Param, DataType

OP_NAME = 'extract_qa_mapper'

DEFAULT_SYSTEM_PROMPT = '''你是一个专业的问答提取助手，你的任务是根据用户提供的文本内容，生成高质量的问答对。

重要规则：
1. 仔细阅读提供的文本内容，理解其中的关键信息
2. 基于文本内容生成多个相关的问题和答案
3. 问题要清晰明确，答案要准确且基于原文
4. 生成的问答对要涵盖文本的主要信息点
5. 严格按照以下格式输出：
   Human: [问题1]
   Assistant: [答案1]
   Human: [问题2]
   Assistant: [答案2]

示例：
输入文本："蒙古国的首都是乌兰巴托（Ulaanbaatar）。它是蒙古国最大的城市，也是该国的政治、经济和文化中心。"

输出格式：
Human: 蒙古国的首都是哪里？
Assistant: 蒙古国的首都是乌兰巴托（Ulaanbaatar）。
Human: 乌兰巴托在蒙古国是什么样的城市？
Assistant: 乌兰巴托是蒙古国最大的城市，也是该国的政治、经济和文化中心。

现在，请根据用户提供的文本内容生成问答对。'''


@OPERATORS.register_module(OP_NAME)
class ExtractQAMapper(Mapper):
    """
    Mapper to extract question and answer pair from text samples using remote API.
    Supports OpenAI-compatible API formats including Qwen, DeepSeek, GPT, etc.
    """

    _accelerator = 'cpu'

    def __init__(self,
                 model_url: str = 'https://api.deepseek.com/v1',
                 model_name: str = 'deepseek-chat',
                 auth_token: str = '',
                 pattern: str = None,
                 qa_format: str = 'chatml',
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.num_proc = 1

        self.model_url = model_url
        self.model_name = model_name
        self.auth_token = auth_token

        if not self.model_url:
            raise ValueError("model_url is required")
        if not self.auth_token:
            raise ValueError("auth_token is required")

        if pattern is None:
            self.pattern = r'Human: (.*?)\nAssistant: (.*?)(?=\nHuman|$)'
        else:
            self.pattern = pattern

        self.qa_format = qa_format
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def _extract_qa(self, output):
        """Extract qestion and answer pair from model output response."""
        qa_list = []

        pat = re.compile(self.pattern, re.DOTALL)
        qa_pairs = pat.findall(output)

        for _, qa in enumerate(qa_pairs, 1):
            user, assistant = qa
            qa_list.append((user.strip(), assistant.strip()))

        return qa_list

    def process(self, sample, rank=None):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        original_text = sample[self.text_key]
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": DEFAULT_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": sample[self.text_key]
                }
            ]

            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }

            data = {
                "model": self.model_name,
                "messages": messages,
                "stream": False
            }

            logger.info(f'Calling API: {self.model_url}, Model: {self.model_name}')

            response = requests.post(
                url=self.model_url,
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            output = result['choices'][0]['message']['content']

            qa_list = self._extract_qa(output)

            if not len(qa_list):
                logger.warning(
                    'No question and answer data was extracted from this sample!')
                if getattr(self, 'enable_detailed_logging', False):
                    self.unmodified_samples += 1
                return sample

            dialogue_data = []
            if self.qa_format == 'chatml':
                for qa in qa_list:
                    dialogue_data.append({
                        'messages': [{
                            'role': 'user',
                            'content': qa[0]
                        }, {
                            'role': 'assistant',
                            'content': qa[1]
                        }]
                    })
            else:
                raise ValueError(f'Not support {self.qa_format}!')

            sample[self.text_key] = json.dumps(dialogue_data, ensure_ascii=False)

            logger.debug(f'QA extraction successful, extracted {len(qa_list)} pairs')
            
            if getattr(self, 'enable_detailed_logging', False):
                self.modified_samples += 1

        except requests.exceptions.RequestException as e:
            logger.error(f'HTTP request error: {e}')
            logger.warning(f'API call failed, keeping original text')
            if getattr(self, 'enable_detailed_logging', False):
                self.unmodified_samples += 1
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f'API response parsing error: {e}')
            logger.warning(f'Response parsing failed, keeping original text')
            if getattr(self, 'enable_detailed_logging', False):
                self.unmodified_samples += 1
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            logger.warning(f'Exception occurred, keeping original text')
            if getattr(self, 'enable_detailed_logging', False):
                self.unmodified_samples += 1

        return sample

    @classmethod
    @property
    def description(cls):
        return """问答提取算子：从文本中提取问答对，将文档转换为对话训练格式。支持千问、DeepSeek、GPT 等 OpenAI 兼容格式的 API。"""

    @classmethod
    @property
    def sample(cls):
        return Sample('蒙古国的首都是乌兰巴托（Ulaanbaatar）。它是蒙古国最大的城市，也是该国的政治、经济和文化中心。',
                      '[{"messages": [{"role": "user", "content": "蒙古国的首都是哪里？"}, {"role": "assistant", "content": "蒙古国的首都是乌兰巴托（Ulaanbaatar）。"}]}, {"messages": [{"role": "user", "content": "乌兰巴托在蒙古国是什么样的城市？"}, {"role": "assistant", "content": "乌兰巴托是蒙古国最大的城市，也是该国的政治、经济和文化中心。"}]}]')

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
    
    def run(self, dataset, *, exporter=None, tracer=None):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples = 0
            self.modified_samples = 0
            self.unmodified_samples = 0
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        return result
    
    def _log_mapper_summary(self):
        try:
            from loguru import logger
            total, modified, unmodified = self.total_samples, self.modified_samples, self.unmodified_samples
            if total == 0: return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Extract QA Summary")
            self._log_line("="*60)
            self._log_line(f"Total: {total}, Extracted: {modified} ({modified/total*100:.2f}%), Failed: {unmodified} ({unmodified/total*100:.2f}%)")
            self._log_line("="*60)
        except: pass
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)