from data_server.logic.constant import BUILDIN_OPS
from data_server.logic.config import build_tools
from typing import Annotated, Union, Literal, Optional
from dataclasses import dataclass
from data_engine.ops.base_op import Sample, Param


@dataclass
class OP:
    name: str
    type: Union[Literal["mapper"], Literal["filter"], Literal["deduplicator"], Literal["selector"]]
    description: str
    samples: Optional[Sample] = None
    params: Optional[list[Param]] = None

async def get_ops(op_type: Annotated[str, "str in 'mapper', 'filter', 'deduplicator' and 'selector'"] = None) -> list[OP] | str:
    return [OP(op_name, op.type, op.description) for op_name, op in BUILDIN_OPS.items() if op_type is None or op.type.lower() == op_type.lower()]

async def get_single_op(op_name: str) -> OP:
    original_op = BUILDIN_OPS[op_name]
    if original_op:
        return OP(op_name, original_op.type, original_op.description, original_op.samples, original_op.params)
    else:
        return "found nothing, I guess the name of the op is incorrect."

@dataclass
class Tool:
    # defination params
    name: str
    description: Optional[str] = None
    type: Optional[Union[Literal["Preprocess"], Literal["Postprocess"], Literal["Common"]]] = None
    params: Optional[list[Param]] = None

BUILDIN_TOOLS = build_tools(userid=None, isadmin=True)
async def get_tools() -> list[Tool]:
    return [Tool(tool_name, tool.description, tool.sub_type, None) for tool_name, tool in BUILDIN_TOOLS.items()]

async def get_single_tool(tool_name: str) -> OP:
    original_tool = BUILDIN_TOOLS[tool_name]
    if original_tool:
        return Tool(tool_name, original_tool.description, original_tool.sub_type, original_tool.params)
    else:
        return "found nothing, I guess the name of the tool is incorrect."

if __name__ == "__main__":
    # print(len(BUILDIN_SAMPLES))  chinese_convert_mapper
    print(get_single_op("chinese_convert_mapper"))
