#!/usr/bin/env python3

import json
import sys
import click
import os

import tempfile
from data_engine.config import init_configs

from loguru import logger
from data_server.logic.models import ExecutedParams
from data_server.logic.utils import exclude_fields_config
from data_server.logic.models import Recipe, Tool

from data_engine.core import Executor
from data_engine.core import ToolExecutor
from data_engine.core import RayExecutor
from data_engine.core import ToolExecutorRay

@click.group()
def cli():
    pass

class JSONParamType(click.ParamType):
    name = "json"

    def convert(self, value, param, ctx):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            self.fail(f"'{value}' is not a valid JSON string", param, ctx)

JSON_TYPE = JSONParamType()

@cli.command() 
@click.option("--config", type=JSON_TYPE, required=True, help="json config")
@click.option("--user-id", type=str, required=True, help="user id")
@click.option("--user-name", type=str, required=True, help="user name")
@click.option("--user-token", type=str, required=True, help="user token")
def tool(config, user_id, user_name, user_token):
    """tool"""
    logger.info(f'tool start')
    try:
        tool = Tool.model_validate_json(config)
        work_dir = os.path.dirname(tool.export_path)
        tool.branch=tool.branch if tool.branch and len(tool.branch) > 0 else 'main'

        params = ExecutedParams(
            user_id=user_id,
            user_name=user_name,
            user_token=user_token,
            work_dir=work_dir,
        )

        if os.environ.get("RAY_ENABLE", "False") == "True":
            executor = ToolExecutorRay(tool_def=tool, params=params)
        else:
            executor = ToolExecutor(tool_def=tool, params=params)
        
        logger.info(f'tool run')
        _, branch_name = executor.run()
    except Exception as e:
        logger.info(f'tool executor.run error with: {str(e)}')
        sys.exit(1)


@cli.command()
@click.option("--config", type=JSON_TYPE, required=True, help="json config")
@click.option("--user-id", type=str, required=True, help="user id")
@click.option("--user-name", type=str, required=True, help="user name")
@click.option("--user-token", type=str, required=True, help="user token")
def pipeline(config, user_id, user_name, user_token):
    """pipeline"""
    logger.info(f'pipeline start')
    try:
        recipe = Recipe.model_validate_json(config)
        yaml_content = recipe.yaml(exclude=exclude_fields_config)

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmpfile:
            tmpfile.write(yaml_content)
            temp_dir_str = tmpfile.name
        cfg = init_configs(['--config', temp_dir_str, '--user_id', user_id,
                                '--user_name', user_name, '--user_token', user_token])

        if os.environ.get("RAY_ENABLE", "False") == "True":
            executor = RayExecutor(cfg)
        else:
            executor = Executor(cfg)
            
        logger.info(f'pipeline run')
        _, branch_name = executor.run()
    except Exception as e:
        logger.info(f'pipeline executor.run error with: {str(e)}')
        sys.exit(1)
    

if __name__ == '__main__':
    cli()  