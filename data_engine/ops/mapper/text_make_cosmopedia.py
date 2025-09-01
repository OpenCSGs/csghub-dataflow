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
        self.model_url = "https://euqnoct5ophc.space.opencsg.com/v1/chat/completions"
        self.model = 'THUDM/LongWriter-glm4-9b'
        self.auth_token = "9acc3ea387b5479607bdeb5386af6e3483fbf070"
        self.content = '''网页摘录：“{web_text}”。
以 WikiHow 的风格写一篇长而非常详细的教程，教程与此网页摘录有相关性。
教程中需要包括对每个步骤的深入解释以及它如何帮助实现预期结果。你可以自由补充其他相关知识。
确保清晰性和实用性，让读者能够轻松遵循教程完成任务。内容中不应包含广告或涉及隐私的信息。
不要使用图像。请直接开始撰写教程。
'''

    def process(self, sample):
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
        sample['data'] = chat_with_model(self.model_url, self.auth_token, self.model, messages=messages)
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
            Param("model_url", DataType.STRING, {}, "https://euqnoct5ophc.space.opencsg.com/v1/chat/completions"),
            Param("model", DataType.STRING, {}, "THUDM/LongWriter-glm4-9b"),
            Param("auth_token", DataType.STRING, {}, "9acc3ea387b5479607bdeb5386af6e3483fbf070"),
            Param("content", DataType.STRING, {}, '''网页摘录：“{web_text}”。
以 WikiHow 的风格写一篇长而非常详细的教程，教程与此网页摘录有相关性。
教程中需要包括对每个步骤的深入解释以及它如何帮助实现预期结果。你可以自由补充其他相关知识。
确保清晰性和实用性，让读者能够轻松遵循教程完成任务。内容中不应包含广告或涉及隐私的信息。
不要使用图像。请直接开始撰写教程。
''')
        ]



