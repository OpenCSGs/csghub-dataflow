import data_engine.tools.legacies.prepare_dataset_from_repo as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'prepare_dataset_from_repo_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class PrepareDatasetFromRepo(TOOL):
    """
    Prepare dataset from code repo with format like this:
    Repository Name, Filepath in the Repository, File Contents
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)

    def process(self):
        legacy.main(src_dir=self.tool_def.dataset_path,
                                  target_dir=self.tool_def.export_path, num_proc=self.tool_def.np)

        # return Path(target_path)
        return Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        Prepare dataset from code repo with format like this:
        Repository Name, Filepath in the Repository, File Contents
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return None
