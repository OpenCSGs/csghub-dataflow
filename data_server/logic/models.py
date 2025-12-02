from typing import Union, Literal, Any, Optional
from pydantic import BaseModel, field_validator
from data_server.schemas import responses
import yaml
from yaml.dumper import SafeDumper
from data_engine.config.config import default_suffixes
from datetime import datetime

def represent_none(self, _):
    return self.represent_scalar('tag:yaml.org,2002:null', '')

SafeDumper.add_representer(type(None), represent_none)

class OperatorIdentifierItem(BaseModel):
    name: str
    index: int

class OperatorIdentifier(BaseModel):
    job_id: int
    operators:list[OperatorIdentifierItem]



class BaseModelExtended(BaseModel):
    @classmethod
    def parse_yaml(cls, file, **kwargs) -> "BaseModelExtended":
        kwargs.setdefault("Loader", yaml.SafeLoader)
        dict_args = yaml.load(file, **kwargs)
        ops_origin = dict_args.pop("process")
        dict_args["process"] = make_ops(ops_origin)

        try:
            return cls.model_validate(dict_args)
        except ValueError as e:
            raise ValueError(f"Invalid values or format in {file.name} with error {e}")

    def yaml(
        self,
        *,
        stream=None,
        include=None,
        exclude=None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        **kwargs,
    ):
        """
        Generate a YAML representation of the recipe, `include` and `exclude` arguments as per `dict()`.
        """
        recipe = self.model_dump(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        ops_origin = recipe.pop("process")
        recipe["process"] = reverse_ops(ops_origin)
        return yaml.dump(
            recipe,
            Dumper=SafeDumper,
            default_flow_style=False,
            stream=stream,
            **kwargs,
        )


class Option(BaseModelExtended):
    key: str
    label: str


class Sample(BaseModelExtended):
    before: str
    after: str


class Param(BaseModelExtended):
    name: str
    type: Optional[Union[Literal["STRING"], Literal["INTEGER"], Literal["FLOAT"],
                Literal["BOOLEAN"], Literal["DICTIONARY"], Literal["TUPLE"], Literal["LIST"], Literal["PositiveFloat"], Literal["ClosedUnitInterval"], Literal["from_2_to_20"], Literal["search-select"], Literal["select-model"]]] = None
    option_values: Optional[list[Option]] = None
    value: Optional[Any] = None
    tempVal: Optional[Any] = None


class Op(BaseModelExtended):
    name: str
    description: Optional[str] = None
    type: Optional[Union[Literal["Formatter"], Literal["Mapper"],
                Literal["Filter"], Literal["Deduplicator"], Literal["Selector"]]] = None
    group: str
    samples: Optional[Sample] = None
    status: Optional[str] = responses.JOB_STATUS.QUEUED.value
    data_lines: int = 0
    data: dict = {}
    params: list[Param]


class Recipe(BaseModelExtended):
    # For orgnized purpose
    # params: Optional[list[Param]] = None
    # mem_required: Optional[int | str] = 0
    # cpu_required: Optional[int] = 1
    # accelerator:Optional[Union[Literal["cpu"], Literal["gpu"]]] = "cpu"

    name: Optional[str] = ""
    description: Optional[str] = None
    template_id: Optional[str] = None
    buildin: Optional[bool] = True
    job_source: str = "pipeline"
    type: Optional[str] = ""
    # global parameters
    project_name: str
    repo_id: Optional[str] = ""
    branch: Optional[str] = "main"
    dataset_path: Optional[str] = None
    export_path: Optional[str] = None
    export_shard_size: int = 0
    export_in_parallel: bool = False
    open_tracer: bool = True
    trace_num: int = 3
    np: int = 3
    text_keys: str = "text"
    suffixes: list = default_suffixes
    use_cache: bool = False
    ds_cache_dir: Optional[str] = None
    use_checkpoint: bool = False
    temp_dir: Optional[str] = None
    op_list_to_trace: list = []
    op_fusion: bool = False
    cache_compress: Optional[Union[Literal["gzip"],
                                   Literal["zstd"], Literal["lz4"]]] = "gzip"
    keep_stats_in_res_ds: bool = False
    keep_hashes_in_res_ds: bool = False

    # for distributed processing
    executor_type: Union[Literal["default"], Literal["ray"]] = "default"
    ray_address: str = "auto"

    # only for data analysis
    percentiles: list = [0.25, 0.5, 0.75]
    export_original_dataset: bool = False
    save_stats_in_one_file: bool = False

    # process schedule: a list of several process operators with their arguments
    process: list[Op]

    dslText: Optional[str] = None

    is_run: Optional[bool]= False
    task_run_time: Optional[datetime] = None

    # @field_validator("process")
    # def process_non_empty(cls, process):
    #     assert len(process) > 0
    #     return process


def make_ops(ops: list) -> list[Op]:
    from .constant import BUILDIN_OPS
    ops_obj: list[Op] = []

    for op_dict in ops:
        op_name = list(op_dict.keys())[0]
        if not op_name in BUILDIN_OPS:
            continue

        op_definition: Op = BUILDIN_OPS[op_name]
        op = op_definition.model_copy(deep=True)

        op_params = op_dict[op_name]
        if op_params:
            for key in op_params.keys():
                for org_param in op.params:
                    if org_param.name == key:
                        org_param.value = op_params[key]

        ops_obj.append(op)

    return ops_obj

def reverse_ops(ops: list):
    ops_reverse: list = []
    for op in ops:
        params = {}
        for param in op["params"]:
            params[param["name"]] = param["value"]

        ops_reverse.append({op["name"]: (params if len(params) > 0 else None)})

    return ops_reverse

class Tool(BaseModel):
    # defination params
    name: str
    description: Optional[str] = None
    type: Optional[Union[Literal["Internal"], Literal["External"]]] = None
    sub_type: Optional[Union[Literal["Preprocess"], Literal["Postprocess"], Literal["Common"]]] = None
    params: Optional[list[Param]] = None
    job_source: str = "tool"

    # excution parameters
    io_requirement: str = "all" # Should be one of ["all", "input_only", "output_only", "none"]
    repo_id: Optional[str] = ""
    project_name: str = "auto"
    branch: Optional[str] = "main"
    dataset_path: Optional[str] = None
    export_path: Optional[str] = None
    export_shard_size: int = 0
    export_in_parallel: bool = False
    np: int = 3
    accelerator: Optional[Union[Literal["cpu"], Literal["gpu"]]] = None
    cpu_required: Optional[int] = 1
    mem_required: Optional[int|str] = 0
    # text_keys: str = "text"
    executor_type: Union[Literal["default"], Literal["ray"]] = "default"
    ray_address: str = "auto"
    keep_stats_in_res_ds: bool = False
    keep_hashes_in_res_ds: bool = False


class ExecutedParams(BaseModel):
    user_id: str
    user_name: str
    user_token: str
    work_dir: str
