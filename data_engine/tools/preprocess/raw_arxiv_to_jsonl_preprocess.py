import data_engine.tools.legacies.raw_arxiv_to_jsonl as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'raw_arxiv_to_jsonl_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class RawArxivtoJsonl(TOOL):
    """
    convert the raw arXiv data(gzipped tar file) into the jsonl format 
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.
        """
        super().__init__(tool_defination, params)

    def process(self):
        target_path = legacy.main(arxiv_src_dir=self.tool_def.dataset_path, target_dir=self.tool_def.export_path,
                                  num_proc=self.tool_def.np)

        return Path(target_path) if target_path else Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
    convert the raw arXiv data(gzipped tar file) into the jsonl format 
    """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return None
