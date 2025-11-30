import sys
from loguru import logger
from .base_tool import TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams

def load_tool(tool: Tool_def, params: ExecutedParams):
    """
    Load tool instance according to the process list from config file.

    :param process_list: A process list. Each item is an op name and its
        arguments.
    :param op_fusion: whether to fuse ops that share the same intermediate
        variables.
    :return: The op instance list.
    """
    tools = TOOLS.modules[tool.name](tool, params)
    for attr, value in tool.model_dump().items():
        tools._attr = value

    return tools

def load_tool_cls(tool: Tool_def):
    """
    Load tool class according to the process list from config file.

    :param process_list: A process list. Each item is an op name and its
        arguments.
    :param op_fusion: whether to fuse ops that share the same intermediate
        variables.
    :return: The op instance list.
    """
    return TOOLS.modules[tool.name]
