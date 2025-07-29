from data_engine.ops.base_op import OPERATORS, Param as OP_PARAM, Sample as OP_SAMPLE, OP
from data_engine.tools.base_tool import TOOL, TOOLS
from data_engine.config.config import sort_op_by_types_and_names, sort_tool_by_types_and_names
from .models import Op, Param, Option, Sample, Recipe, Tool
import glob
import os
import yaml
import pathlib

TEMPLATE_DIR = 'configs/templates'

def build_ops():
    ops_sorted_by_types = sort_op_by_types_and_names(OPERATORS.modules.items())
    ops: dict(str, Op) = {}

    op_class: OP = None
    for op_name, op_class in ops_sorted_by_types:
        if not op_class.description:
            continue

        params: list[Param] = []
        if op_class.init_params:
            param: OP_PARAM = None
            for param in op_class.init_params:
                options = [Option(key=key, label=param.options[key])
                           for key in param.options.keys()] if param.options else None
                params.append(Param(
                    name=param.name,
                    type=param.type.name,
                    option_values=options,
                    value=param.default
                ))

        op_sample: OP_SAMPLE = op_class.sample
        ops[op_name] = Op(
            name=op_name,
            description=op_class.description,
            type=str(op_name.split("_")[-1]).capitalize(),
            group="",
            samples=Sample(before=op_sample.before, after=op_sample.after),
            params=params,
        )

    return ops

def build_templates(userid: str = None, isadmin: bool = False):
    base_dir = pathlib.Path().resolve()
    template_path = os.path.join(base_dir, TEMPLATE_DIR)
    # print(f"loading template from path: {template_path}")

    file_list = sorted(glob.glob(os.path.join(template_path, '*.yaml')))

    templates: list[Recipe] = []
    for file in file_list:
        with open(file,encoding="utf-8") as stream:
            try:
                recipe_model: Recipe = Recipe.parse_yaml(stream)
                # if recipe_model.buildin or (isadmin or os.path.basename(file).split("_")[0] == userid):
                #     templates.append(recipe_model)
                templates.append(recipe_model)
            except yaml.YAMLError as exc:
                print(exc)
    return templates

def build_templates_with_filepath(userid: str = None, isadmin: bool = False):
    base_dir = pathlib.Path().resolve()
    template_path = os.path.join(base_dir, TEMPLATE_DIR)
    # print(f"loading template from path: {template_path}")

    file_list = sorted(glob.glob(os.path.join(template_path, '*.yaml')))

    templates: dict(str, Recipe) = {}
    is_windows = os.name == 'nt'
    for file in file_list:
        if is_windows:
            with open(file, encoding="utf-8", errors="ignore") as stream:
                try:
                    recipe_model: Recipe = Recipe.parse_yaml(stream)
                    if recipe_model.buildin or (isadmin or os.path.basename(file).split("_")[0] == userid):
                        templates[os.path.basename(file)] = recipe_model
                except yaml.YAMLError as exc:
                    print(exc)
        else:
            with open(file) as stream:
                try:
                    recipe_model: Recipe = Recipe.parse_yaml(stream)
                    if recipe_model.buildin or (isadmin or os.path.basename(file).split("_")[0] == userid):
                        templates[os.path.basename(file)] = recipe_model
                except yaml.YAMLError as exc:
                    print(exc)
    return templates

def build_tools(userid: str = None, isadmin: bool = False):
    tools_sorted_by_types = sort_tool_by_types_and_names(TOOLS.modules.items())
    tools: dict(str, TOOL) = {}

    tool_class: TOOL = None
    for tool_name, tool_class in tools_sorted_by_types:
        if not tool_class.description:
            continue

        params: list[Param] = []
        if hasattr(tool_class, 'init_params'):
            if tool_class.init_params(userid, isadmin) is not None:
                for param in tool_class.init_params(userid, isadmin):
                    options = [Option(key=key, label=param.options[key])
                            for key in param.options.keys()] if param.options else None
                    params.append(Param(
                        name=param.name,
                        type=param.type.name,
                        option_values=options,
                        value=param.default
                    ))

        tools[tool_name] = Tool(
            name=tool_name,
            description=tool_class.description,
            sub_type=str(tool_name.split("_")[-2]).capitalize(),
            type=str(tool_name.split("_")[-1]).capitalize(),
            params=params,
        )
        if tool_class.io_requirement:
            tools[tool_name].io_requirement=tool_class.io_requirement

    return tools
