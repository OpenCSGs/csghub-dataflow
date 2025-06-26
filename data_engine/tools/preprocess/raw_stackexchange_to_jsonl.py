import data_engine.tools.legacies.raw_stackexchange_to_jsonl as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'raw_stackexchange_to_jsonl_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class RawStackexchangetoJsonl(TOOL):
    """
    Convert the raw Stack Exchange data downloaded from from Archive
    (ref: https://archive.org/download/stackexchange) to several
    jsonl files.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param topk: select the topk sites with the most content.
                  Default it's 28.
        """
        super().__init__(tool_defination, params)
        self.topk = next(
            (item.value for item in self.tool_def.params if item.name == "topk"), 28)

    def process(self):
        target_path = legacy.main(src_dir=self.tool_def.dataset_path, target_dir=self.tool_def.export_path,
                                  topk=self.topk, num_proc=self.tool_def.np)

        return Path(target_path) if target_path else Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return  """
        Convert the raw Stack Exchange data downloaded from from Archive
        (ref: https://archive.org/download/stackexchange) to several
        jsonl files.
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("topk", DataType.INTEGER, None, 28)
        ]
