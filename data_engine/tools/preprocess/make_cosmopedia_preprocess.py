import data_engine.tools.legacies.make_cosmopedia as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'cosmopedia_chinese_preprocess_internal'

@TOOLS.register_module(TOOL_NAME)
class makeCosmopediaPreprocessInternal(TOOL):
    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)

        self.web_text_max_len = next(
            (item.value for item in self.tool_def.params if item.name == "web_text_max_len"), 800)
        self.model_url = next(
            (item.value for item in self.tool_def.params if item.name == "model_url"), 
            "https://euqnoct5ophc.space.opencsg.com/v1/chat/completions")
        self.model = next(
            (item.value for item in self.tool_def.params if item.name == "model"), 
            "THUDM/LongWriter-glm4-9b")
        self.auth_token = next(
            (item.value for item in self.tool_def.params if item.name == "auth_token"), 
            "9acc3ea387b5479607bdeb5386af6e3483fbf070")
        self.content = next(
            (item.value for item in self.tool_def.params if item.name == "content"), 
            '''网页摘录："{web_text}"。
以 WikiHow 的风格写一篇长而非常详细的教程，教程与此网页摘录有相关性。
教程中需要包括对每个步骤的深入解释以及它如何帮助实现预期结果。你可以自由补充其他相关知识。
确保清晰性和实用性，让读者能够轻松遵循教程完成任务。内容中不应包含广告或涉及隐私的信息。
不要使用图像。请直接开始撰写教程。''')

    def process(self):
        legacy.main(
            src_dir = self.tool_def.dataset_path,
            target_dir = self.tool_def.export_path,
            num_proc = self.tool_def.np,
            web_text_max_len = self.web_text_max_len,
            model_url = self.model_url,
            model = self.model,
            auth_token = self.auth_token,
            content = self.content
        )

        return Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        A detailed tutorial on converting raw text to WikiHow style using the MakeCosmopediaMapper operator.
        This tool invokes large language models to generate structured tutorial content based on the input seed text.
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("web_text_max_len", DataType.INTEGER, None, 800),
            Param("model_url", DataType.STRING, None, "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
            Param("model", DataType.STRING, None, "qwen-plus"),
            Param("auth_token", DataType.STRING, None, ""),
            Param("content", DataType.STRING, None, '''网页摘录："{web_text}"。
以 WikiHow 的风格写一篇长而非常详细的教程，教程与此网页摘录有相关性。
教程中需要包括对每个步骤的深入解释以及它如何帮助实现预期结果。你可以自由补充其他相关知识。
确保清晰性和实用性，让读者能够轻松遵循教程完成任务。内容中不应包含广告或涉及隐私的信息。
不要使用图像。请直接开始撰写教程。''')
        ]