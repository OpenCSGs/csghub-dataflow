import data_engine.tools.legacies.count_token as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'count_token_postprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class CountToken(TOOL):
    """
    Count the number of tokens for given dataset and tokenizer. 
    Only support 'jsonl' now.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)
        self.text_keys = next(
            (item.value for item in self.tool_def.params if item.name == "text_keys"), None)
        self.tokenizer_method = next(
            (item.value for item in self.tool_def.params if item.name == "tokenizer_method"), None)

    def process(self):
        legacy.main(data_path=self.tool_def.dataset_path, text_keys=self.text_keys,
                                  tokenizer_method=self.tokenizer_method, num_proc=self.tool_def.np)

        return Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        Count the number of tokens for given dataset and tokenizer. 
        Only support 'jsonl' now.
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("text_keys", DataType.STRING, None, None),
            Param("tokenizer_method", DataType.STRING, {
                "EleutherAI/pythia-6.9b-deduped": "EleutherAI/pythia-6.9b-deduped"
            }, "EleutherAI/pythia-6.9b-deduped"),
        ]
