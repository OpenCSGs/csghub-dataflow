# Some code here has been modified from:
# https://github.com/yuyijiong/fineweb-edu-chinese/
# --------------------------------------------------------

from ..base_op import OPERATORS, Mapper, Sample,Param,DataType
from ..common import chat_with_model

OP_NAME = 'make_cosmopedia_mapper'

@OPERATORS.register_module(OP_NAME)
class MakeCosmopediaMapper(Mapper):
    """Mapper to generate synthetic tutorial data from seed text samples."""

    # _batched_op = False

    def __init__(self, *args, **kwargs):
        """
        Initialization method.

        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.web_text_max_len = 800
        self.model_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.model = 'qwen-plus'
        self.auth_token = ""
        self.content = '''网页摘录："{web_text}"。
以 WikiHow 的风格写一篇长而非常详细的教程，教程与此网页摘录有相关性。
教程中需要包括对每个步骤的深入解释以及它如何帮助实现预期结果。你可以自由补充其他相关知识。
确保清晰性和实用性，让读者能够轻松遵循教程完成任务。内容中不应包含广告或涉及隐私的信息。
不要使用图像。请直接开始撰写教程。
'''
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.generated_samples = 0
        self.failed_samples = 0

    def process(self, sample):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        
        if 'content' in sample and 'text' not in sample:
            sample['text'] = sample.pop('content')
        if 'md' in sample and 'text' not in sample:
            sample['text'] = sample.pop('md')
        web_text = sample.get('title', '') + '\n' + sample['text']
        web_text = web_text[:self.web_text_max_len] + "......" if len(web_text) > self.web_text_max_len else web_text
        messages = [
            {
                "role": "system",
                "content": "你是一个乐于助人的助手"
            },
            {
                "role": "user",
                "content": self.content.format(web_text=web_text),
            }
        ]
        
        try:
            sample['data'] = chat_with_model(self.model_url, self.auth_token, self.model, messages=messages)
            if getattr(self, 'enable_detailed_logging', False):
                if sample.get('data'):
                    self.generated_samples += 1
                else:
                    self.failed_samples += 1
        except Exception as e:
            if getattr(self, 'enable_detailed_logging', False):
                self.failed_samples += 1
            sample['data'] = ""
        
        return sample

    @classmethod
    @property
    def description(cls):
        return """Mapper to generate synthetic tutorial data from seed text samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample(
            'How to Train Your Dog to Sit',
            'Training your dog to sit is one of the most fundamental commands...'
        )

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("web_text_max_len", DataType.STRING, {}, 800),
            Param("model_url", DataType.STRING, {}, "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
            Param("model", DataType.STRING, {}, "qwen-plus"),
            Param("auth_token", DataType.STRING, {}, ""),
            Param("content", DataType.STRING, {}, '''网页摘录："{web_text}"。
以 WikiHow 的风格写一篇长而非常详细的教程，教程与此网页摘录有相关性。
教程中需要包括对每个步骤的深入解释以及它如何帮助实现预期结果。你可以自由补充其他相关知识。
确保清晰性和实用性，让读者能够轻松遵循教程完成任务。内容中不应包含广告或涉及隐私的信息。
不要使用图像。请直接开始撰写教程。
''')
        ]
    
    def run(self, dataset, *, exporter=None, tracer=None):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples = 0
            self.generated_samples = 0
            self.failed_samples = 0
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        return result
    
    def _log_mapper_summary(self):
        try:
            from loguru import logger
            total, generated, failed = self.total_samples, self.generated_samples, self.failed_samples
            if total == 0: return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Cosmopedia Tutorial Generation Summary")
            self._log_line("="*60)
            self._log_line(f"Total: {total}, Generated: {generated} ({generated/total*100:.2f}%), Failed: {failed} ({failed/total*100:.2f}%)")
            self._log_line("="*60)
        except: pass
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)
