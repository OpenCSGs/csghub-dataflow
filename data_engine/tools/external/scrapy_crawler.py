import data_engine.tools.legacies.dataset_split_by_language as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'scrapy_crawler_preprocess_external'

@TOOLS.register_module(TOOL_NAME)
class ScrapyCrawler(TOOL):
    """
    xxxxxxx
    for this tool, I think after the user click the tool card, the detail page should just show a description(details)
    and just have one lauch button, will call the process function and return a url and automatic open the url
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)
        # handle params you required
        # TODO

    def process(self):
        # maybe startup the instance of scrapy and return url of that instance ?
        return Path("")

    @classmethod
    @property
    def description(cls):
        return """
        xxxxxx
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("suffixes", DataType.LIST, None, [])
        ]
