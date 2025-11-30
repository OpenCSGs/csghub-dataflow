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

# Import all required operators to ensure they are registered
from data_engine.ops.mapper.pipeline_magpie_zh_mapper import PipelineMagpieZh
from data_engine.ops.filter.text_gather_filter import TextGatherFilter
from data_engine.ops.edu.encode_and_get_nearest import EncodeAndGetNearestSelector
from data_engine.ops.deduplicator.dedup_and_save_deduplicator import DedupAndSaveDeduplicator

TOOL_NAME = 'smoltalk_chinese_common_internal'


@TOOLS.register_module(TOOL_NAME)
class TemplateExecutorSe(TOOL):

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):

        super().__init__(tool_defination, params)
        self.template_path = next(
            (item.value for item in self.tool_def.params if item.name == "template_path"), None)
        self.model_url = next(
            (item.value for item in self.tool_def.params if item.name == "model_url"), None)
        self.model_name = next(
            (item.value for item in self.tool_def.params if item.name == "model_name"), None)
        self.auth_token = next(
            (item.value for item in self.tool_def.params if item.name == "auth_token"), None)
        # embedding_model_parameters
        self.embedding_model_url = next(
            (item.value for item in self.tool_def.params if item.name == "embedding_model_url"), None)
        self.embedding_model_name = next(
            (item.value for item in self.tool_def.params if item.name == "embedding_model_name"), None)
        self.embedding_auth_token = next(
            (item.value for item in self.tool_def.params if item.name == "embedding_auth_token"), None)
        self.similarity_threshold = next(
            (item.value for item in self.tool_def.params if item.name == "similarity_threshold"), None)

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
            logger.info(f"self.tool_def:{self.tool_def}")
            cfg = init_configs([
                '--config', temp_name,
                '--user_id', self.executed_params.user_id,
                '--user_name', self.executed_params.user_name,
                '--user_token', self.executed_params.user_token,
                '--np', str(self.tool_def.np),
                '--tool_name', TOOL_NAME,
                # '--dataset_path', self.tool_def.dataset_path,
                '--export_path', self.tool_def.export_path,
            ])

            cfg.work_dir = self.executed_params.work_dir
            
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
        Use a fixed system_prompt to generate relevant multi-round dialogues with a large model and score them. Filter the data based on the score specified by the user, and only retain the one with the highest score.
        """

    @classmethod
    @property
    def io_requirement(cls):
        return "output_only"
    
    def _update_operator_params(self, recipe: Recipe):
        for op in recipe.process:
            if op.name == 'pipeline_magpie_zh_mapper':
                for param in op.params:
                    if param.name == 'model_url' and self.model_url:
                        param.value = self.model_url
                    elif param.name == 'model_name' and self.model_name:
                        param.value = self.model_name
                    elif param.name == 'auth_token' and self.auth_token:
                        param.value = self.auth_token
            elif op.name == 'encode_and_get_nearest_mapper':
                for param in op.params:
                    if param.name == 'model_url' and self.embedding_model_url:
                        param.value = self.embedding_model_url
                    elif param.name == 'model_name' and self.embedding_model_name:
                        param.value = self.embedding_model_name
                    elif param.name == 'auth_token' and self.embedding_auth_token:
                        param.value = self.embedding_auth_token
            elif op.name == 'dedup_and_save_deduplicator':
                for param in op.params:
                    if param.name == 'similarity_threshold' and self.similarity_threshold is not None:
                        param.value = self.similarity_threshold


    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        from data_server.logic.config import build_templates_with_filepath

        # Only load the 06-smoltalk-chinese.yaml template
        templates: dict = build_templates_with_filepath(userid, isadmin)
        filtered_templates = {k: v for k, v in templates.items() if k == '06-smoltalk-chinese.yaml'}
        options = {value.name: key for key, value in filtered_templates.items()}
        default = options[next(iter(options))] if options else ""
        
        return [
            Param("template_path", DataType.STRING, options, default),
            Param("model_url", DataType.STRING, None, "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            Param("model_name", DataType.STRING, None, "qwen-plus"),
            Param("auth_token", DataType.STRING, None, ""),
            # embedding_model_parameters
            Param("embedding_model_url", DataType.STRING, None, "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            Param("embedding_model_name", DataType.STRING, None, "text-embedding-v4"),
            Param("embedding_auth_token", DataType.STRING, None, ""),
            Param("similarity_threshold", DataType.FLOAT, None, 0.5),
        ]
