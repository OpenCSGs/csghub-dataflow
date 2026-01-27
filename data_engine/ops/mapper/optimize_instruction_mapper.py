import requests
import json

from loguru import logger

from data_engine.ops.base_op import OPERATORS, Mapper, Sample, Param, DataType

DEFAULT_SYSTEM_PROMPT = '''你是一个专业的指令优化助手，你的唯一任务是将用户输入的简单问题或指令扩展为更详细、更具体、更全面的指令版本。

重要规则：
1. 你不要回答用户的问题，你只需要将问题本身扩展得更详细
2. 你不要提供问题的答案或解决方案，只需要让问题变得更加详细和具体
3. 在扩展指令时，要明确需要哪些方面的详细信息、具体步骤、注意事项等
4. 保持原问题的核心意图不变，只是让它变得更加详细和结构化

示例：
输入："今天天气怎么样？"
正确输出："请提供今天的详细天气信息，包括：1）当前温度和体感温度；2）天气状况（晴天、多云、雨天等）；3）湿度和风力情况；4）空气质量指数(AQI)；5）未来3-6小时的天气变化趋势；6）适合的穿衣建议和出行提示。"
错误输出："今天天气晴朗，温度25度。"（这是在回答问题，而不是扩展问题）

输入："怎么做蛋炒饭？"
正确输出："请提供制作蛋炒饭的完整指导，包括：1）所需食材清单及用量（米饭、鸡蛋、配菜、调味料等）；2）食材的准备工作（米饭处理技巧、配菜切法等）；3）详细的烹饪步骤和火候控制；4）调味的时机和技巧；5）常见问题的解决方法（如何避免粘锅、如何让米饭粒粒分明等）；6）营养搭配建议。"

现在，请将用户输入的指令扩展为更详细、更具体的版本。记住：不要回答问题，只扩展问题！'''

OP_NAME = 'optimize_instruction_mapper'


@OPERATORS.register_module(OP_NAME)
class OptimizeInstructionMapper(Mapper):
    _accelerator = 'cpu'

    def __init__(self,
                 model_url: str = 'https://api.deepseek.com/chat/completions',
                 model_name: str = 'deepseek-chat',
                 auth_token: str = '',
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
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.optimized_samples = 0
        self.failed_samples = 0

    def process(self, sample=None, rank=None):
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
            optimized_text = result['choices'][0]['message']['content']
            
            sample[self.text_key] = optimized_text
            
            logger.debug(f'Instruction optimization successful')
            
            if getattr(self, 'enable_detailed_logging', False):
                if optimized_text != original_text:
                    self.optimized_samples += 1
                else:
                    self.failed_samples += 1
            
        except requests.exceptions.RequestException as e:
            logger.error(f'HTTP request error: {e}')
            logger.warning(f'API call failed, keeping original text')
            if getattr(self, 'enable_detailed_logging', False):
                self.failed_samples += 1
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f'API response parsing error: {e}')
            logger.warning(f'Response parsing failed, keeping original text')
            if getattr(self, 'enable_detailed_logging', False):
                self.failed_samples += 1
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            logger.warning(f'Exception occurred, keeping original text')
            if getattr(self, 'enable_detailed_logging', False):
                self.failed_samples += 1
        
        return sample

    @classmethod
    @property
    def description(cls):
        return """指令优化算子：将简单的用户问题优化为详细、具体的指令。支持千问、DeepSeek、GPT 等 OpenAI 兼容格式的 API。"""

    @classmethod
    @property
    def sample(cls):
        return Sample('鱼香肉丝怎么做？',
                    '请提供一份完整的"鱼香肉丝"食谱，包括以下详细信息：'
                    '所需材料清单：请列出所有必要的主料和辅料，包括肉的种类和处理方式，以及所有蔬菜和调味料的具体量。'
                    '准备工作指南：描述准备工作的具体步骤，如肉丝的腌制过程、蔬菜的切割技巧等。'
                    '详细烹饪步骤：请按照烹饪的逻辑顺序，逐步解释如何将材料炒制成鱼香肉丝，包括火候控制、调味料添加的时机等详细操作。'
                    '盛盘和陈设建议：给出如何将完成的鱼香肉丝装盘摆放，以及可以搭配的其他菜品或饭类推荐，以便提升整体用餐体验。'
                    '附加小贴士：如有任何专业小窍门或注意事项，例如如何切肉更易入味，或特定调味料的选择建议等，也请一并提供。')

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
            self.optimized_samples = 0
            self.failed_samples = 0
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        return result
    
    def _log_mapper_summary(self):
        try:
            from loguru import logger
            total, optimized, failed = self.total_samples, self.optimized_samples, self.failed_samples
            if total == 0: return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Instruction Optimization Summary")
            self._log_line("="*60)
            self._log_line(f"Total: {total}, Optimized: {optimized} ({optimized/total*100:.2f}%), Failed: {failed} ({failed/total*100:.2f}%)")
            self._log_line("="*60)
        except: pass
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)