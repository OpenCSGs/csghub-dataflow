import data_engine.tools.legacies.analyzer as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, Recipe, ExecutedParams
from data_server.logic.utils import exclude_fields_config
from pathlib import Path
from data_engine.config import init_configs
import os
import pathlib
import tempfile
from loguru import logger

TOOL_NAME = 'analysis_common_internal'


@TOOLS.register_module(TOOL_NAME)
class Analysis(TOOL):
    """
    This Analyzer class is used to analyze a specific dataset.

    It will compute stats for all filter ops in the config file, apply
    multiple analysis (e.g. OverallAnalysis, ColumnWiseAnalysis, etc.)
    on these stats, and generate the analysis results (stats tables,
    distribution figures, etc.) to help users understand the input
    dataset better.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)
        self.tempalte_path = next(
            (item.value for item in self.tool_def.params if item.name == "template_path"), None)
        self.text_key = next(
            (item.value for item in self.tool_def.params if item.name == "text_key"), None)


    def process(self):
        from data_server.logic.config import TEMPLATE_DIR

        base_dir = pathlib.Path().resolve()
        template_path = os.path.join(
            base_dir, TEMPLATE_DIR, self.tempalte_path)
        
        with open(template_path) as stream:
            recipe: Recipe = Recipe.parse_yaml(stream)
            recipe_content = recipe.yaml(
                exclude=exclude_fields_config)
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmpfile:
            tmpfile.write(recipe_content)
            temp_name = tmpfile.name
        cfg = init_configs(['--config', temp_name, '--user_id', self.executed_params.user_id,
                            '--user_name', self.executed_params.user_name, '--user_token', self.executed_params.user_token, '--np', str(self.tool_def.np),
                            '--dataset_path', self.tool_def.dataset_path, '--export_path', self.tool_def.export_path])
        os.remove(temp_name)  # Delete temp file

        # cfg.dataset_path = self.tool_def.dataset_path
        # cfg.export_path = self.tool_def.export_path
        cfg.work_dir = self.executed_params.work_dir
        cfg.text_keys = self.text_key


        legacy.main(cfg=cfg)

        # return a fake path means the tools do generated something but do not expect to upload to somewhere
        return Path(os.path.join(self.tool_def.export_path, 'fake'))

    @classmethod
    @property
    def description(cls):
        return """
        This Analyzer class is used to analyze a specific dataset.

        It will compute stats for all filter ops in the config file, apply
        multiple analysis (e.g. OverallAnalysis, ColumnWiseAnalysis, etc.)
        on these stats, and generate the analysis results (stats tables,
        distribution figures, etc.) to help users understand the input
        dataset better.
        """

    @classmethod
    @property
    def io_requirement(cls):
        return "input_only"
    
    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        from data_server.logic.config import build_templates_with_filepath
        templates: dict(str, Recipe) = build_templates_with_filepath(userid, isadmin)
        options = {value.name: key
                   for key, value in templates.items()}
        default = options[next(iter(options))]
        return [
            Param("template_path", DataType.STRING, options, default),
            Param("text_key", DataType.STRING, None, "text"),
        ]
