import os
import json
import shutil
import tempfile
from types import SimpleNamespace

from loguru import logger

from data_engine.exporter.load import load_exporter
from data_engine.format.load import load_formatter
from data_engine.ingester.load import load_ingester
from data_engine.ops import load_ops
from data_server.datasource.DatasourceModels import DataSourceTypeEnum
from data_server.datasource.schemas import DataSourceCreate
from data_server.datasource.services.datasource import get_datasource_connector
from data_server.formatify.FormatifyModels import DataFormatTypeEnum
from data_server.logic.models import ExecutedParams, Recipe, Tool
from data_server.logic.utils import exclude_fields_config, strip_recipe_scheduler_fields
from data_engine.config import init_configs
from data_engine.core import ToolExecutor, ToolExecutorRay
from data_engine.core.tracer import Tracer
from data_engine.ops import OPERATORS
from data_server.pod.trace_sync_client import sync_output_trace
from data_server.pod.datasource_helpers import (
    convert_mongo_document,
    hive_get_table_dataset,
    hive_get_table_dataset_by_sql,
    mysql_get_table_dataset,
    mysql_get_table_dataset_by_sql,
)
from data_server.pod.job_progress import (
    build_operator_run_progress,
    normalize_tool_run_progress,
)
from data_server.pod.pod_logger import log_task_error, log_task_info
from data_server.pod.formatify_helpers import (
    convert_excel_to_csv,
    convert_excel_to_json,
    convert_excel_to_parquet,
    convert_word_to_markdown,
    convert_txt_to_markdown,
    convert_html_to_markdown,
    convert_ppt_to_markdown,
    convert_pdf_to_markdown,
    search_files,
)

def get_data_dir() -> str:
    """Work dir: DATA_DIR env only (set in template.env when DataFlow submits to CSGHub)."""
    explicit = os.getenv("DATA_DIR", "").strip().rstrip("/")
    if explicit:
        return explicit
    return "/dataflow_data"


def get_flow_base_dir(flow_id: str) -> str:
    return os.path.join(get_data_dir(), "argo", flow_id)


def get_input_dir(flow_id: str) -> str:
    return os.path.join(get_flow_base_dir(flow_id), "input")


def get_output_dir(flow_id: str) -> str:
    """Pipeline/Tool matches legacy JobWorkflow: work dir is output/ (log/, trace/)."""
    return os.path.join(get_flow_base_dir(flow_id), "output")


def get_pipeline_export_file(flow_id: str) -> str:
    return os.path.join(get_output_dir(flow_id), "_df_dataset.jsonl")


def get_task_stage_dir(flow_id: str, task_name: str) -> str:
    """Datasource/Formatify still use stages subdirs per task name."""
    return os.path.join(get_flow_base_dir(flow_id), "stages", sanitize_task_name(task_name))


def get_task_output_file(flow_id: str, task_name: str) -> str:
    return os.path.join(get_task_stage_dir(flow_id, task_name), "_df_dataset.jsonl")


def resolve_pipeline_input_path(flow_id: str, input_source_task: str) -> str:
    """
    Operator 1 reads input/; later operators read previous step data only (output/_data or exported jsonl).

    Do not use entire output/ as dataset_path: it contains trace/count-*.txt, log, config;
    load_formatter may pick TextFormatter by suffix count and treat trace stats as dataset,
    causing missing text_key (e.g. access_key) errors.
    """
    if input_source_task == "pull_data":
        return get_input_dir(flow_id)

    output_dir = get_output_dir(flow_id)
    data_dir = _resolve_pipeline_tool_data_upload_dir(output_dir)
    if data_dir:
        return data_dir

    nested_export = os.path.join(output_dir, "_data", "_df_dataset.jsonl")
    if os.path.isfile(nested_export):
        return nested_export

    legacy_export = get_pipeline_export_file(flow_id)
    if os.path.isfile(legacy_export):
        return legacy_export

    logger.warning(
        "flow_id={} previous step has no output/_data; fallback to entire output dir {}",
        flow_id,
        output_dir,
    )
    return output_dir


def sanitize_task_name(task_name: str) -> str:
    return task_name.replace(" ", "_").replace("/", "_")


def _mark_collection_task_failed(task_params: dict, error_message: str):
    task_uid = task_params.get("task_uid")
    if task_uid:
        log_task_error(task_uid, error_message)


def _build_datasource_from_params(task_params: dict) -> DataSourceCreate:
    extra_config = task_params.get("extra_config")
    if isinstance(extra_config, str):
        try:
            extra_config = json.loads(extra_config)
        except Exception:
            extra_config = {}
    return DataSourceCreate(
        name=str(task_params.get("datasource_name") or ""),
        des=str(task_params.get("datasource_des") or ""),
        source_type=int(task_params.get("source_type")),
        host=str(task_params.get("host") or ""),
        auth_type=task_params.get("auth_type"),
        port=task_params.get("port"),
        username=task_params.get("username"),
        password=task_params.get("password"),
        database=str(task_params.get("database") or ""),
        extra_config=extra_config or {},
        source_status=task_params.get("source_status"),
        cluster_id=task_params.get("cluster_id"),
        cluster_name=task_params.get("cluster_name"),
        resource_id=task_params.get("resource_id"),
        resource_name=task_params.get("resource_name"),
    )


def _build_collection_context(task_params: dict):
    return SimpleNamespace(
        task_uid=str(task_params.get("task_uid") or ""),
        total_count=0,
        records_count=0,
    )


def _resolve_file_source_path(datasource, extra_config: dict) -> str:
    extra_config = extra_config or {}
    candidates = [
        extra_config.get("file_path"),
        extra_config.get("path"),
        datasource.host,
        datasource.database,
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _count_files_in_path(source_path: str) -> int:
    if os.path.isfile(source_path):
        return 1
    total = 0
    for _, _, files in os.walk(source_path):
        total += len(files)
    return total


def _copy_file_source_to_stage(source_path: str, stage_dir: str) -> str:
    os.makedirs(stage_dir, exist_ok=True)
    if os.path.isdir(source_path):
        source_name = os.path.basename(os.path.normpath(source_path)) or "source"
        target_path = os.path.join(stage_dir, source_name)
        shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        return target_path

    target_path = os.path.join(stage_dir, os.path.basename(source_path))
    shutil.copy2(source_path, target_path)
    return target_path


def _resolve_pipeline_tool_data_upload_dir(output_dir: str) -> str | None:
    """
    Same as legacy JobExecutor / ExporterCSGHUB._export_common:
    upload data product dir (work_dir/_data) only, not entire output/ (trace, log, config, etc.).
    """
    candidates = [
        os.path.join(output_dir, "_df_dataset.jsonl", "_data"),  # tool base_tool.export_path
        os.path.join(output_dir, "_data"),  # operator/pipeline exporter.export -> output/_data/*.jsonl
        os.path.join(output_dir, "converted"),
    ]
    for path in candidates:
        if os.path.isdir(path) and os.listdir(path):
            return path
    return None


def _resolve_stage_export_path(flow_id: str, upload_source_task: str) -> tuple[str, str]:
    """Return (export_path, source_dir). Collection/conversion read stages/; Pipeline/Tool read data subdirs only."""
    if upload_source_task == "pull_data":
        input_dir = get_input_dir(flow_id)
        return input_dir, input_dir
    flow_prefix = str(flow_id or "")[:2]
    if flow_prefix == "AA":
        stage_dir = get_task_stage_dir(flow_id, upload_source_task)
        return stage_dir, stage_dir
    if flow_prefix == "AB":
        stage_dir = get_task_stage_dir(flow_id, upload_source_task)
        converted_dir = os.path.join(stage_dir, "converted")
        export_path = converted_dir if os.path.isdir(converted_dir) else stage_dir
        return export_path, stage_dir
    output_dir = get_output_dir(flow_id)
    data_dir = _resolve_pipeline_tool_data_upload_dir(output_dir)
    if data_dir:
        return data_dir, output_dir
    # Operator/tool: do not fall back to entire output/ without data subdir (avoid uploading trace, log, config)
    return "", output_dir


def _describe_missing_stage_dir(flow_id: str, expected_path: str) -> str:
    data_dir = get_data_dir()
    base_dir = get_flow_base_dir(flow_id)
    stages_dir = os.path.join(base_dir, "stages")
    parts = [f"DATA_DIR={data_dir}", f"expected={expected_path}"]
    if os.path.isfile(expected_path):
        parts.append("path exists but is a file, not a directory")
    elif not os.path.exists(expected_path):
        parts.append("path does not exist")
    if os.path.isdir(stages_dir):
        parts.append(f"stages under flow: {os.listdir(stages_dir)}")
    elif os.path.isdir(base_dir):
        parts.append(f"flow base exists, children: {os.listdir(base_dir)}")
    else:
        parts.append(f"flow base missing: {base_dir}")
    parts.append(
        "若前一 Pod 已成功但当前 Pod 看不到目录，请检查 Argo 是否使用共享 PVC（RWX），"
        "且 CSGHub 将 workflow-data 的 volume mountPath 配置为与 Pod 环境变量 DATA_DIR 相同"
    )
    return "; ".join(parts)


def _config_dict_from_task_params(task_params: dict) -> dict:
    config = task_params.get("config")
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except Exception:
            config = {}
    return config if isinstance(config, dict) else {}


def _resolve_upload_target(task_params: dict) -> tuple[str | None, str]:
    """Upload target repo/branch; Pipeline/Tool must use config.repo_id, not pull job.repo_id."""
    config = _config_dict_from_task_params(task_params)
    repo_id = (
        task_params.get("to_csg_hub_repo_id")
        or task_params.get("export_repo_id")
        or config.get("repo_id")
    )
    branch = (
        task_params.get("to_csg_hub_dataset_default_branch")
        or task_params.get("export_branch_name")
        or config.get("branch")
        or task_params.get("branch")
        or "main"
    )
    extra_config = task_params.get("extra_config")
    if isinstance(extra_config, str):
        try:
            extra_config = json.loads(extra_config)
        except Exception:
            extra_config = {}
    if isinstance(extra_config, dict):
        repo_id = repo_id or extra_config.get("csg_hub_dataset_id")
        branch = (
            extra_config.get("csg_hub_dataset_default_branch")
            or extra_config.get("csg_hub_dataset_branch")
            or branch
        )
    if not repo_id:
        repo_id = task_params.get("repo_id")
    return repo_id, branch


def run_pull_data(task_params: dict):
    flow_id = task_params["flow_id"]
    input_dir = get_input_dir(flow_id)
    os.makedirs(input_dir, exist_ok=True)

    repo_id = task_params.get("from_csg_hub_repo_id") or task_params.get("repo_id")
    branch = task_params.get("from_csg_hub_dataset_branch") or task_params.get("branch") or "main"
    user_name = str(task_params.get("user_name") or "")
    user_token = str(task_params.get("user_token") or "")

    if not repo_id:
        logger.info("No repo_id found for pull_data, creating shared workspace only")
        return input_dir

    ingester = load_ingester(
        dataset_path=input_dir,
        repo_id=repo_id,
        branch=branch,
        user_name=user_name,
        user_token=user_token,
    )
    return ingester.ingest()


def run_upload_data(task_params: dict):
    flow_id = task_params["flow_id"]
    upload_source_task = task_params.get("upload_source_task")
    if not upload_source_task:
        raise ValueError("upload_source_task is required")

    export_path, _source_dir = _resolve_stage_export_path(flow_id, upload_source_task)
    flow_prefix = str(flow_id or "")[:2]
    if not export_path:
        if flow_prefix in ("AC", "AD"):
            logger.info(
                "upload_data skipped: no data dir under output/_data "
                "(tool may have uploaded in tool_execute) flow_id={} task={}",
                flow_id,
                upload_source_task,
            )
            repo_id, branch = _resolve_upload_target(task_params)
            return {
                "upload_repo_id": repo_id,
                "upload_branch": branch,
                "upload_skipped": True,
            }
        raise FileNotFoundError(
            f"No upload path for flow_id={flow_id} upload_source_task={upload_source_task}"
        )
    if not os.path.isdir(export_path):
        raise FileNotFoundError(_describe_missing_stage_dir(flow_id, export_path))
    if not os.listdir(export_path):
        raise FileNotFoundError(
            f"Upload directory is empty: {export_path}. "
            f"Check whether data_harvesting ({upload_source_task}) exported any files."
        )
    path_is_dir = True

    repo_id, branch = _resolve_upload_target(task_params)
    if not repo_id or not str(repo_id).strip():
        raise ValueError(
            "upload_data requires target repo_id (export_repo_id / to_csg_hub_repo_id / config.repo_id)"
        )
    user_name = str(task_params.get("user_name") or "")
    user_token = str(task_params.get("user_token") or "")
    work_dir = os.path.join(get_output_dir(flow_id), "upload_work")
    os.makedirs(work_dir, exist_ok=True)

    exporter = load_exporter(
        export_path=export_path,
        repo_id=repo_id,
        branch=branch,
        user_name=user_name,
        user_token=user_token,
        work_dir=work_dir,
        path_is_dir=path_is_dir,
        auto_version=True,
    )
    max_retries = int(task_params.get("upload_max_retries") or 3)
    for attempt in range(1, max_retries + 1):
        try:
            upload_branch = exporter.export_large_folder()
            task_uid = task_params.get("task_uid")
            if task_uid:
                log_task_info(
                    task_uid,
                    f"Datasource upload_data finished successfully, branch={upload_branch or branch}",
                )
            return {
                "upload_repo_id": repo_id,
                "upload_branch": upload_branch or branch,
            }
        except Exception:
            logger.exception(f"upload_data failed on attempt {attempt}/{max_retries}")
            if attempt >= max_retries:
                raise
    return {"upload_repo_id": repo_id, "upload_branch": branch}


def run_tool_execute(task_params: dict):
    flow_id = task_params["flow_id"]
    input_dir = get_input_dir(flow_id)
    output_dir = get_output_dir(flow_id)
    os.makedirs(output_dir, exist_ok=True)

    tool = Tool.model_validate(task_params["config"])
    tool.dataset_path = input_dir
    tool.export_path = get_pipeline_export_file(flow_id)
    tool.branch = tool.branch if tool.branch and len(tool.branch) > 0 else "main"

    params = ExecutedParams(
        user_id=str(task_params.get("user_id") or ""),
        user_name=str(task_params.get("user_name") or ""),
        user_token=str(task_params.get("user_token") or ""),
        work_dir=output_dir,
    )
    if os.environ.get("RAY_ENABLE", "False") == "True":
        executor = ToolExecutorRay(tool_def=tool, params=params)
    else:
        executor = ToolExecutor(tool_def=tool, params=params)
    run_result = executor.run()
    return normalize_tool_run_progress(run_result)


def run_operator_execute(task_params: dict):
    flow_id = task_params["flow_id"]
    input_source_task = task_params.get("input_source_task")
    if not input_source_task:
        raise ValueError("input_source_task is required")

    output_dir = get_output_dir(flow_id)
    os.makedirs(output_dir, exist_ok=True)
    input_path = resolve_pipeline_input_path(flow_id, input_source_task)

    config = strip_recipe_scheduler_fields(task_params.get("config") or {})
    process = config.get("process") or []
    if not process:
        raise ValueError("operator config requires process with exactly one operator")
    if len(process) > 1:
        operator_name = task_params.get("operator_name")
        if operator_name:
            matched = [op for op in process if (op.get("name") if isinstance(op, dict) else getattr(op, "name", None)) == operator_name]
            process = matched[:1] if matched else process[:1]
        else:
            process = process[:1]
    recipe = Recipe.model_validate(config)
    if len(recipe.process) != 1:
        raise ValueError(f"operator config must contain one process entry, got {len(recipe.process)}")
    recipe.dataset_path = input_path
    recipe.export_path = get_pipeline_export_file(flow_id)
    recipe.repo_id = ""

    yaml_content = recipe.yaml(exclude=exclude_fields_config)
    if input_source_task == "pull_data":
        with open(os.path.join(output_dir, "config.yaml"), mode="w", encoding="utf-8") as file:
            file.write(yaml_content)
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmpfile:
        tmpfile.write(yaml_content)
        temp_path = tmpfile.name

    try:
        cfg = init_configs([
            "--config", temp_path,
            "--user_id", str(task_params.get("user_id") or ""),
            "--user_name", str(task_params.get("user_name") or ""),
            "--user_token", str(task_params.get("user_token") or ""),
        ], redirect=False)
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                logger.warning("Failed to remove temp operator config {}", temp_path)

    formatter = load_formatter(
        recipe.dataset_path,
        cfg.generated_dataset_config,
        cfg.text_keys,
        cfg.suffixes,
        cfg.add_suffix,
    )
    dataset = formatter.load_dataset(cfg.np, cfg)
    ops = load_ops(cfg.process, cfg.op_fusion, job_uid=str(task_params.get("job_id") or ""))
    exporter = load_exporter(
        recipe.export_path,
        cfg.export_shard_size,
        cfg.export_in_parallel,
        cfg.np,
        repo_id=None,
        branch=None,
        user_name=str(task_params.get("user_name") or ""),
        user_token=str(task_params.get("user_token") or ""),
        work_dir=output_dir,
        auto_version=False,
    )
    tracer = None
    if getattr(cfg, "open_tracer", False):
        tracer = Tracer(output_dir, show_num=getattr(cfg, "trace_num", 3) or 3)
        op_list_to_trace = getattr(cfg, "op_list_to_trace", None) or []
        if not op_list_to_trace:
            op_list_to_trace = list(OPERATORS.modules.keys())
    dataset = dataset.process(ops, exporter=exporter, tracer=tracer)
    result = exporter.export(dataset)
    operator_name = task_params.get("operator_name") or (
        recipe.process[0].name if recipe.process else None
    )
    sync_output_trace(
        flow_id=flow_id,
        output_dir=output_dir,
        operator_name=operator_name,
        user_token=task_params.get("user_token"),
        job_id=task_params.get("job_id"),
        operator_index=task_params.get("operator_index"),
    )
    try:
        operator_index = int(task_params.get("operator_index") or 0)
    except (TypeError, ValueError):
        operator_index = 0
    progress = build_operator_run_progress(
        output_dir=output_dir,
        operator_name=str(operator_name or ""),
        operator_index=operator_index,
        export_file=get_pipeline_export_file(flow_id),
    )
    if isinstance(result, dict):
        return {**progress, **result}
    return progress


def _summarize_stage_dir(stage_dir: str) -> str:
    if not os.path.isdir(stage_dir):
        return f"stage_dir missing: {stage_dir}"
    entries = os.listdir(stage_dir)
    if not entries:
        return f"stage_dir empty: {stage_dir}"
    parts = []
    for name in entries[:20]:
        path = os.path.join(stage_dir, name)
        if os.path.isdir(path):
            parts.append(f"{name}/({len(os.listdir(path))} files)")
        else:
            parts.append(name)
    suffix = " ..." if len(entries) > 20 else ""
    return f"stage_dir={stage_dir}, entries=[{', '.join(parts)}{suffix}]"


def run_data_harvesting(task_params: dict):
    flow_id = task_params["flow_id"]
    current_task_name = task_params["current_task_name"]
    stage_dir = get_task_stage_dir(flow_id, current_task_name)
    os.makedirs(stage_dir, exist_ok=True)
    logger.info(
        "data_harvesting start | flow_id={} | task={} | DATA_DIR={} | stage_dir={}",
        flow_id,
        current_task_name,
        get_data_dir(),
        stage_dir,
    )
    datasource = _build_datasource_from_params(task_params)
    collection_task = _build_collection_context(task_params)
    extra_config = datasource.extra_config or {}
    connector = get_datasource_connector(datasource)
    test_result = connector.test_connection()
    if isinstance(test_result, dict):
        if not test_result.get("success", False):
            raise RuntimeError(test_result.get("message", "Datasource connection failed"))
    elif not test_result:
        raise RuntimeError("Datasource connection failed")

    if datasource.source_type == DataSourceTypeEnum.MYSQL.value:
        mysql_cfg = extra_config.get("mysql", {})
        _run_sql_or_tables(
            source_type="mysql",
            connector=connector,
            config=mysql_cfg,
            task_uid=collection_task.task_uid,
            collection_task=collection_task,
            stage_dir=stage_dir,
            max_line=extra_config.get("max_line_json", 10000),
        )
    elif datasource.source_type == DataSourceTypeEnum.HIVE.value:
        hive_cfg = extra_config.get("hive", {})
        _run_sql_or_tables(
            source_type="hive",
            connector=connector,
            config=hive_cfg,
            task_uid=collection_task.task_uid,
            collection_task=collection_task,
            stage_dir=stage_dir,
            max_line=extra_config.get("max_line_json", 10000),
        )
    elif datasource.source_type == DataSourceTypeEnum.MONGODB.value:
        mongo_cfg = extra_config.get("mongo", {})
        _run_mongo_collection(
            connector=connector,
            mongo_cfg=mongo_cfg,
            task_uid=collection_task.task_uid,
            collection_task=collection_task,
            stage_dir=stage_dir,
            max_line=extra_config.get("max_line_json", 10000),
        )
    elif datasource.source_type == DataSourceTypeEnum.FILE.value:
        source_path = _resolve_file_source_path(datasource, extra_config)
        if not source_path or not os.path.exists(source_path):
            raise ValueError("FILE datasource source path not found")
        total_count = _count_files_in_path(source_path)
        collection_task.total_count = total_count
        collection_task.records_count = 0
        log_task_info(collection_task.task_uid, f"Start collecting FILE datasource from: {source_path}")
        copied_path = _copy_file_source_to_stage(source_path, stage_dir)
        collection_task.records_count = total_count
        log_task_info(
            collection_task.task_uid,
            f"FILE datasource collection finished, copied to: {copied_path}, file_count: {total_count}",
        )
    else:
        raise ValueError(f"Unsupported datasource type: {datasource.source_type}")

    records_count = getattr(collection_task, "records_count", 0) or 0
    if records_count == 0 and not os.listdir(stage_dir):
        raise RuntimeError(
            f"data_harvesting produced no output under {stage_dir}. "
            "Check mysql.source column names or sql result in datasource extra_config, "
            "and collection task logs in DataFlow UI."
        )
    logger.info(
        "data_harvesting finished | flow_id={} | records_count={} | {}",
        flow_id,
        records_count,
        _summarize_stage_dir(stage_dir),
    )
    total_count = getattr(collection_task, "total_count", 0) or records_count
    return {
        "stage_dir": stage_dir,
        "records_count": records_count,
        "total_count": total_count,
    }


def _run_sql_or_tables(source_type: str, connector, config: dict, task_uid: str, collection_task, stage_dir: str, max_line: int):
    use_type = config.get("type", "")
    use_sql = config.get("sql", "")
    if use_type == "sql":
        if not use_sql:
            raise ValueError(f"{source_type} datasource sql is empty")
        if source_type == "mysql":
            mysql_get_table_dataset_by_sql(connector, task_uid, use_sql, collection_task, stage_dir, max_line=max_line)
        else:
            hive_get_table_dataset_by_sql(connector, task_uid, use_sql, collection_task, stage_dir, max_line=max_line)
        return

    source_tables = config.get("source")
    if not source_tables:
        raise ValueError(f"{source_type} datasource source config is empty")
    total_count = 0
    if source_type == "mysql":
        for table_name in source_tables.keys():
            total_count += connector.get_table_total_count(table_name)
    else:
        for table_name in source_tables.keys():
            total_count += connector.get_table_total_count_hive(table_name)
    collection_task.total_count = total_count
    collection_task.records_count = 0

    logger.info(
        "data_harvesting tables | source_type={} | tables={} | total_count={} | stage_dir={}",
        source_type,
        list(source_tables.keys()),
        total_count,
        stage_dir,
    )
    for table_name, config_columns in source_tables.items():
        if source_type == "mysql":
            mysql_get_table_dataset(connector, task_uid, collection_task, table_name, config_columns, stage_dir, max_line=max_line)
        else:
            hive_get_table_dataset(connector, task_uid, collection_task, table_name, config_columns, stage_dir, max_line=max_line)


def _run_mongo_collection(connector, mongo_cfg: dict, task_uid: str, collection_task, stage_dir: str, max_line: int):
    total_count = 0
    for collection_name in mongo_cfg:
        total_count += connector.get_collection_document_count(collection_name)
    collection_task.total_count = total_count
    collection_task.records_count = 0

    import pandas as pd
    for collection_name in mongo_cfg:
        table_dir = os.path.join(stage_dir, collection_name)
        os.makedirs(table_dir, exist_ok=True)
        page_size = 10000
        page = 1
        file_index = 1
        rows_buffer = []
        records_count = collection_task.records_count or 0
        while True:
            rows = connector.query_collection(collection_name, offset=(page - 1) * page_size, limit=page_size)
            if not rows:
                break
            converted_rows = [convert_mongo_document(row) for row in (rows if isinstance(rows, list) else list(rows))]
            rows_buffer.extend(converted_rows)
            if len(rows_buffer) >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                pd.DataFrame(rows_buffer).to_parquet(file_path, index=False)
                records_count += len(rows_buffer)
                collection_task.records_count = records_count
                rows_buffer = []
                file_index += 1
            page += 1
        if rows_buffer:
            file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
            pd.DataFrame(rows_buffer).to_parquet(file_path, index=False)
            records_count += len(rows_buffer)
            collection_task.records_count = records_count


def run_format_conversion(task_params: dict):
    flow_id = task_params["flow_id"]
    current_task_name = task_params["current_task_name"]
    input_dir = get_input_dir(flow_id)
    stage_dir = get_task_stage_dir(flow_id, current_task_name)
    raw_dir = os.path.join(stage_dir, "raw")
    os.makedirs(stage_dir, exist_ok=True)
    if os.path.exists(raw_dir):
        shutil.rmtree(raw_dir)
    shutil.copytree(input_dir, raw_dir)

    found, found_files = search_files(raw_dir, [task_params.get("from_data_type")])
    if not found:
        raise ValueError("No source files found for format conversion")

    convert_func = _select_convert_func(task_params.get("from_data_type"), task_params.get("to_data_type"))
    if convert_func is None:
        raise ValueError("Unsupported format conversion")

    output_dir = os.path.join(stage_dir, "converted")
    os.makedirs(output_dir, exist_ok=True)
    success_count = 0
    failure_count = 0
    meta_enabled = bool(task_params.get("skip_meta"))
    meta_entries = []
    used_names = {}
    for root, _, files in os.walk(raw_dir):
        for file in files:
            file_path_full = os.path.join(root, file)
            result = _run_convert_func(convert_func, file_path_full, str(task_params.get("task_uid") or formatify_id), task_params)
            if not isinstance(result, dict):
                continue
            from_file = result.get("from") or file_path_full
            to_file = result.get("to")
            to_files = result.get("to_files")  # Support for multiple output files
            status = result.get("status")
            try:
                from_rel_path = str(os.path.relpath(from_file, raw_dir)).replace("\\", "/")
            except Exception:
                from_rel_path = os.path.basename(from_file)

            # Handle multiple output files (e.g., from multi-sheet Excel)
            if status == "success" and to_files:
                # Process multiple files
                for src_path in to_files:
                    if os.path.exists(src_path):
                        file_name = os.path.basename(src_path)
                        if file_name in used_names:
                            name_part, ext_part = os.path.splitext(file_name)
                            counter = used_names[file_name]
                            file_name = f"{name_part}_{counter}{ext_part}"
                            used_names[os.path.basename(src_path)] += 1
                        else:
                            used_names[file_name] = 1
                        dst_path = os.path.join(output_dir, file_name)
                        shutil.copy2(src_path, dst_path)
                        success_count += 1
                        if meta_enabled:
                            meta_entries.append({
                                "from": from_rel_path,
                                "to": file_name.replace("\\", "/"),
                                "status": "success",
                            })
            elif status == "success" and to_file:
                # Handle single file (backward compatible)
                if isinstance(to_file, list):
                    # If to_file is a list, process all files
                    for src_path in to_file:
                        if os.path.exists(src_path):
                            file_name = os.path.basename(src_path)
                            if file_name in used_names:
                                name_part, ext_part = os.path.splitext(file_name)
                                counter = used_names[file_name]
                                file_name = f"{name_part}_{counter}{ext_part}"
                                used_names[os.path.basename(src_path)] += 1
                            else:
                                used_names[file_name] = 1
                            dst_path = os.path.join(output_dir, file_name)
                            shutil.copy2(src_path, dst_path)
                            success_count += 1
                            if meta_enabled:
                                meta_entries.append({
                                    "from": from_rel_path,
                                    "to": file_name.replace("\\", "/"),
                                    "status": "success",
                                })
                elif os.path.exists(to_file):
                    # Single file (original behavior)
                    src_path = to_file
                    file_name = os.path.basename(src_path)
                    if file_name in used_names:
                        name_part, ext_part = os.path.splitext(file_name)
                        counter = used_names[file_name]
                        file_name = f"{name_part}_{counter}{ext_part}"
                        used_names[os.path.basename(src_path)] += 1
                    else:
                        used_names[file_name] = 1
                    dst_path = os.path.join(output_dir, file_name)
                    shutil.copy2(src_path, dst_path)
                    success_count += 1
                    if meta_enabled:
                        meta_entries.append({
                            "from": from_rel_path,
                            "to": file_name.replace("\\", "/"),
                            "status": "success",
                        })
            else:
                failure_count += 1
                if meta_enabled:
                    entry = {
                        "from": from_rel_path,
                        "to": None,
                        "status": "failure",
                    }
                    if result.get("error"):
                        entry["error"] = result["error"]
                    meta_entries.append(entry)

    if meta_enabled:
        _write_format_meta_log(
            output_dir=output_dir,
            task_params=task_params,
            formatify_id=int(task_params.get("formatify_id") or task_params.get("id") or 0),
            total_count=len(found_files),
            success_count=success_count,
            failure_count=failure_count,
            entries=meta_entries,
        )
    return output_dir


def _select_convert_func(from_type, to_type):
    mapping = {
        (DataFormatTypeEnum.Excel.value, DataFormatTypeEnum.Csv.value): convert_excel_to_csv,
        (DataFormatTypeEnum.Excel.value, DataFormatTypeEnum.Json.value): convert_excel_to_json,
        (DataFormatTypeEnum.Excel.value, DataFormatTypeEnum.Parquet.value): convert_excel_to_parquet,
        (DataFormatTypeEnum.Word.value, DataFormatTypeEnum.Markdown.value): convert_word_to_markdown,
        (DataFormatTypeEnum.PPT.value, DataFormatTypeEnum.Markdown.value): convert_ppt_to_markdown,
        (DataFormatTypeEnum.PDF.value, DataFormatTypeEnum.Markdown.value): convert_pdf_to_markdown,
        (DataFormatTypeEnum.Txt.value, DataFormatTypeEnum.Markdown.value): convert_txt_to_markdown,
        (DataFormatTypeEnum.Html.value, DataFormatTypeEnum.Markdown.value): convert_html_to_markdown,
    }
    return mapping.get((from_type, to_type))


def _run_convert_func(convert_func, file_path: str, task_uid: str, task_params: dict):
    if convert_func is convert_pdf_to_markdown:
        return convert_func(
            file_path,
            task_uid,
            task_params.get("mineru_api_url"),
            task_params.get("mineru_backend"),
        )
    return convert_func(file_path, task_uid)


def _write_format_meta_log(
    *,
    output_dir: str,
    task_params: dict,
    formatify_id: int,
    total_count: int,
    success_count: int,
    failure_count: int,
    entries: list[dict],
):
    meta_dir = os.path.join(output_dir, "meta")
    os.makedirs(meta_dir, exist_ok=True)
    meta_file_path = os.path.join(meta_dir, "meta.log")
    meta_data = {
        "job_id": formatify_id,
        "job_name": task_params.get("name"),
        "source_repo": task_params.get("from_csg_hub_repo_id"),
        "source_branch": task_params.get("from_csg_hub_dataset_branch"),
        "files": entries,
        "result": {
            "total": total_count,
            "success": success_count,
            "failure": failure_count,
        },
    }
    with open(meta_file_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2, ensure_ascii=False)
