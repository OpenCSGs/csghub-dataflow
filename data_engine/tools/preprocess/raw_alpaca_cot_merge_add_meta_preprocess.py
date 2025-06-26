import data_engine.tools.legacies.raw_alpaca_cot_merge_add_meta as legacy

from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'raw_alpaca_cot_merge_add_meta_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class RawAlpacacotMerge(TOOL):
    """
    This tool is used for converting the raw Alpaca-Cot data downloaded from HuggingFace to jsonl files
    Merge `instruction`/`input`/`output` to `text` for process,
    and add meta info.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
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
    This tool is used for converting the raw Alpaca-Cot data downloaded from HuggingFace to jsonl files
    Merge `instruction`/`input`/`output` to `text` for process,
    and add meta info.
    """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return None
