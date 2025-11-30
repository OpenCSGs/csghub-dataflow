import data_engine.tools.legacies.reformat_csv_nan_value as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'reformat_csv_nan_value_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class ReformatCSVNAN(TOOL):
    """
    Reformat csv or tsv files that may contain Nan values using HuggingFace
    to load with extra args, e.g. set `keep_default_na` to False
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)
        self.suffixes = next(
            (item.value for item in self.tool_def.params if item.name == "suffixes"), ['.csv'])
        self.is_tsv = next(
            (item.value for item in self.tool_def.params if item.name == "is_tsv"), False)
        self.keep_default_na = next(
            (item.value for item in self.tool_def.params if item.name == "keep_default_na"), False)

    def process(self):
        target_path = legacy.main(src_dir=self.tool_def.dataset_path, target_dir=self.tool_def.export_path,
                                  suffixes=self.suffixes, is_tsv=self.is_tsv, keep_default_na=self.keep_default_na, num_proc=self.tool_def.np)

        return Path(target_path) if target_path else Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        Reformat csv or tsv files that may contain Nan values using HuggingFace
        to load with extra args, e.g. set `keep_default_na` to False
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("suffixes", DataType.LIST, None, ['.csv']),
            Param("is_tsv", DataType.BOOLEAN, None, False),
            Param("keep_default_na", DataType.BOOLEAN, None, False),
        ]
