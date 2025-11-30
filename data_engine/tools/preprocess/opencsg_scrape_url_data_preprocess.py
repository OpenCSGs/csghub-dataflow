from data_engine.tools.legacies.opencsg_scrapegraphai import scrape_main

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'opencsg_scrape_url_data_preprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class URLDataScrape(TOOL):
    """
    Data scrape tool based on large language model for websites and native documents (XML, HTML, JSON, etc.).
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.
        :param target_dir: path to store subset files(`jsonl` format)
        :param url: Enter the URL to scrape
        :param prompt: prompt to AI description of what data do you want scrape from url.
        """
        super().__init__(tool_defination, params)
        self.url = next(
            (item.value for item in self.tool_def.params if item.name == "url"), None)
        self.prompt = next(
            (item.value for item in self.tool_def.params if item.name == "prompt"), None)

    def process(self):
        scrape_main(self.tool_def.export_path, self.url, self.prompt)
        return Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        Data scrape tool based on large language model for websites and native documents (XML, HTML, JSON, etc.).
        """

    @classmethod
    @property
    def io_requirement(cls):
        return "output_only"

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("url", DataType.STRING, None,
                  'https://top.baidu.com/board?tab=realtime'),
            Param("prompt", DataType.STRING, None,
                  'Give me all the news with their abstracts'),
        ]
