import os
import pathlib
import tempfile
from pathlib import Path
from loguru import logger

from data_engine.core.executor import Executor
from data_engine.config import init_configs
from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, Recipe, ExecutedParams
from data_server.logic.utils import exclude_fields_config

TOOL_NAME = 'fineweb_edu_chinese_common_internal'


@TOOLS.register_module(TOOL_NAME)
class TemplateExecutor(TOOL):

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):

        super().__init__(tool_defination, params)
        self.template_path = next(
            (item.value for item in self.tool_def.params if item.name == "template_path"), None)
        self.text_key = next(
            (item.value for item in self.tool_def.params if item.name == "text_key"), None)
        self.model_url = next(
            (item.value for item in self.tool_def.params if item.name == "model_url"), None)
        self.dimensions = next(
            (item.value for item in self.tool_def.params if item.name == "dimensions"), None)
        self.model_name = next(
            (item.value for item in self.tool_def.params if item.name == "model_name"), None)
        self.auth_token = next(
            (item.value for item in self.tool_def.params if item.name == "auth_token"), None)
        self.query_text = next(
            (item.value for item in self.tool_def.params if item.name == "query_text"), None)
        self.min_score = next(
            (item.value for item in self.tool_def.params if item.name == "min_score"), None)
        self.max_score = next(
            (item.value for item in self.tool_def.params if item.name == "max_score"), None)


        logger.info(f"TemplateExecutor_received_parameters: model_url={self.model_url}, dimensions={self.dimensions}, model_name={self.model_name}, auth_token={'***' if self.auth_token else None}")

    def process(self):

        from data_server.logic.config import TEMPLATE_DIR, build_templates_with_filepath

        base_dir = pathlib.Path().resolve()

        # If template_path is a Chinese name, it needs to be mapped to the actual file name
        templates = build_templates_with_filepath()
        actual_filename = None
        # filename:05-fineweb-edu-chinese.yaml
        # recipe.name:"chinese"
        # self.template_path:"chinese"
        for filename, recipe in templates.items():
            if recipe.name == self.template_path:
                actual_filename = filename
                break

        if actual_filename is None:
            actual_filename = self.template_path
            
        template_path = os.path.join(base_dir, TEMPLATE_DIR, actual_filename)
        
        logger.info(f"Loading template from: {template_path}")
        
        # parseTemplateConfiguration
        with open(template_path, encoding='utf-8') as stream:
            recipe: Recipe = Recipe.parse_yaml(stream)

            self._update_operator_params(recipe)
            
            recipe_content = recipe.yaml(exclude=exclude_fields_config)
        
        # createATemporaryConfigurationFile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as tmpfile:
            tmpfile.write(recipe_content)
            temp_name = tmpfile.name
        
        try:
            # Initialize the configuration and read the required data, including templates
            logger.info(f"dataset_path:{self.tool_def.dataset_path}")
            logger.info(f"export_path:{self.tool_def.export_path}")
            cfg = init_configs([
                '--config', temp_name,
                '--user_id', self.executed_params.user_id,
                '--user_name', self.executed_params.user_name,
                '--user_token', self.executed_params.user_token,
                '--np', str(self.tool_def.np),
                '--dataset_path', self.tool_def.dataset_path,
                '--export_path', self.tool_def.export_path,
                '--text_keys', self.text_key
            ])

            cfg.work_dir = self.executed_params.work_dir
            cfg.text_keys = self.text_key
            
            logger.info(f"Starting template execution with {len(cfg.process)} operators")

            executor = Executor(cfg=cfg)
            dataset, output_branch_name = executor.run()
            
            logger.info(f"Template execution completed. Dataset exported to: {self.tool_def.export_path}")
            
            return Path(self.tool_def.export_path)

        finally:
            pass

    @classmethod
    @property
    def description(cls):
        return """
        Users can define their own scoring criteria, score the data from the data source based on these criteria, and filter the data. The maximum score is 5.
        """

    @classmethod
    @property
    def io_requirement(cls):
        return "all"
    
    def _update_operator_params(self, recipe: Recipe):
        for op in recipe.process:
            if op.name == 'annotate_edu_train_bert_scorer_mapper':
                logger.info(f"find_the_operator {op.name}，start_updating_the_parameters")
                for param in op.params:
                    if param.name == 'model_url' and self.model_url:
                        param.value = self.model_url
                        param.tempVal = self.model_url
                    elif param.name == 'dimensions' and self.dimensions:
                        param.value = self.dimensions
                        param.tempVal = self.dimensions
                    elif param.name == 'model_name' and self.model_name:
                        param.value = self.model_name
                        param.tempVal = self.model_name
                    elif param.name == 'auth_token' and self.auth_token:
                        param.value = self.auth_token
                        param.tempVal = self.auth_token
                    elif param.name == 'query_text' and self.query_text:
                        param.value = self.query_text
                        param.tempVal = self.query_text
                    elif param.name == 'text_key' and self.text_key:
                        param.value = self.text_key
                        param.tempVal = self.text_key
            if op.name == 'text_high_score_filter':
                for param in op.params:
                    if param.name == 'min_score' and self.min_score:
                        param.value = float(self.min_score)
                        param.tempVal = float(self.min_score)
                    elif param.name == 'max_score' and self.max_score:
                        param.value = float(self.max_score)
                        param.tempVal = float(self.max_score)
                    elif param.name == 'score_field' and self.text_key:
                        param.value = f"{self.text_key}_score"
                        param.tempVal = f"{self.text_key}_score"


    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        from data_server.logic.config import build_templates_with_filepath
        
        # Only load the 05-fineweb-edu-chinese.yaml template
        templates: dict = build_templates_with_filepath(userid, isadmin)
        filtered_templates = {k: v for k, v in templates.items() if k == '05-fineweb-edu-chinese.yaml'}
        options = {value.name: key for key, value in filtered_templates.items()}
        default = options[next(iter(options))] if options else ""
        
        return [
            Param("template_path", DataType.STRING, options, default),
            Param("text_key", DataType.STRING, None, "text"),
            Param("model_url", DataType.STRING, None, "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            Param("dimensions", DataType.INTEGER, None, 1024),
            Param("model_name", DataType.STRING, None, "text-embedding-v4"),
            Param("auth_token", DataType.STRING, None, ""),
            Param("min_score", DataType.FLOAT, None, 0),
            # Param("max_score", DataType.FLOAT, None, 5),
            Param("query_text", DataType.STRING, None, "What is Deep Learning?")
        ]
