import data_engine.tools.legacies.dataset_split_by_language as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path
from data_engine.config.config import default_suffixes

TOOL_NAME = 'dataset_spliter_by_language_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class DatasetSpliterbyLang(TOOL):
    """
    Load dataset from the source directory, then apply language identification
    using the operation filter called `LanguageIDScoreFilter`,
    finally, split the dataset by language and save it.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)
        self.suffixes = next(
            (item.value for item in self.tool_def.params if item.name == "suffixes"), None)
        self.text_key = next(
            (item.value for item in self.tool_def.params if item.name == "text_key"), None)

    def process(self):
        target_path = legacy.main(src_dir=self.tool_def.dataset_path, target_dir=self.tool_def.export_path,
                                  text_key=self.text_key, suffixes=self.suffixes, num_proc=self.tool_def.np)

        # return Path(target_path)
        return Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        Load dataset from the source directory, then apply language identification
        using the operation filter called `LanguageIDScoreFilter`,
        finally, split the dataset by language and save it.
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("suffixes", DataType.LIST, None, default_suffixes),
            Param("text_key", DataType.STRING, None, None),
        ]
