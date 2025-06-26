import data_engine.tools.legacies.serialize_meta as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'serialize_meta_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class SerializeMeta(TOOL):
    """
    Serialize all the fields in the jsonl file except the fields specified
    by users to ensure that the jsonl file with inconsistent text format
    for each line can also be load normally by the dataset.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param serialized_key: the key corresponding to the field that the
        serialized info saved. Default it's 'source_info'.
        """
        super().__init__(tool_defination, params)
        self.serialized_key = next(
            (item.value for item in self.tool_def.params if item.name == "serialized_key"), 'source_info')
        self.text_key = next(
            (item.value for item in self.tool_def.params if item.name == "text_key"), None)

    def process(self):
        target_path = legacy.main(src_dir=self.tool_def.dataset_path, target_dir=self.tool_def.export_path,
                                  text_key=self.text_key, serialized_key=self.serialized_key, num_proc=self.tool_def.np)

        return Path(target_path) if target_path else Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return  """
        Serialize all the fields in the jsonl file except the fields specified
        by users to ensure that the jsonl file with inconsistent text format
        for each line can also be load normally by the dataset.
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("serialized_key", DataType.STRING, None, 'source_info'),
            Param("text_key", DataType.STRING, None, None),
        ]
