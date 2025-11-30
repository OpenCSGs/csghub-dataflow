import data_engine.tools.legacies.reformat_jsonl_nan_value as legacy

from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'reformat_jsonl_nan_value_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class ReformatJsonlNAN(TOOL):
    """
    Reformat the jsonl files which may contain Nan values. Traverse jsonl
    files to find the first object that does not contain Nan as a
    reference feature type, then set it for loading all jsonl files.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        """
        super().__init__(tool_defination, params)

    def process(self):
        target_path = legacy.main(src_dir=self.tool_def.dataset_path, target_dir=self.tool_def.export_path,
                                  num_proc=self.tool_def.np)

        return Path(target_path) if target_path else Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
    Reformat the jsonl files which may contain Nan values. Traverse jsonl
    files to find the first object that does not contain Nan as a
    reference feature type, then set it for loading all jsonl files.
    """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return None
