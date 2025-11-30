import data_engine.tools.legacies.deserialize_meta as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'deserialize_meta_postprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class DeserializeMeta(TOOL):
    """
    Deserialize the specified field in the jsonl file.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param serialized_key: the key corresponding to the field that will be
            deserialized. Default it's 'source_info'.
        """
        super().__init__(tool_defination, params)
        self.serialized_key = next(
            (item.value for item in self.tool_def.params if item.name == "serialized_key"), None)

    def process(self):
        target_path = legacy.main(src_dir=self.tool_def.dataset_path,
                                  target_dir=self.tool_def.export_path,
                                  serialized_key=self.serialized_key,
                                  num_proc=self.tool_def.np)

        return Path(target_path) if target_path else Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        Deserialize the specified field in the jsonl file.
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("serialized_key", DataType.STRING, None, None),
        ]
