import json
from typing import Any

from data_server.formatify.FormatifyModels import getFormatTypeName
from data_server.utils.csghub_argo_naming import (
    make_dag_task_id,
    resolve_dag_dep_node_names,
    resolve_dag_node_name,
    to_argo_task_type_param,
)
from data_server.utils.csghub_client import build_container_template_name
from data_server.utils.csghub_pipeline_config import (
    build_per_operator_config,
    split_task_params_without_config,
)

def _build_dag_task(
    *,
    flow_id: str,
    sequence: int,
    task_name: str,
    task_type: str,
    task_params: dict[str, Any],
    dep_sequences: list[int] | None = None,
    template_name: str,
) -> dict[str, Any]:
    task_id = make_dag_task_id(flow_id, sequence)
    node_name = resolve_dag_node_name(task_id=task_id, logical_name=task_name)
    enriched_params = {
        **task_params,
        "flow_id": flow_id,
        "current_task_name": task_name,
        "current_task_type": task_type,
        "argo_dag_task_id": task_id,
        "argo_dag_node_name": node_name,
    }
    item: dict[str, Any] = {
        "id": task_id,
        "name": node_name,
        "logical_name": task_name,
        "template": template_name,
        "parameters": [
            {"name": "task_type", "value": to_argo_task_type_param(task_type)},
            {"name": "task_params", "value": json.dumps(enriched_params, ensure_ascii=False)},
        ],
    }
    if dep_sequences:
        item["deps"] = resolve_dag_dep_node_names(flow_id, dep_sequences)
    return item


def _format_short_name(value: int | None) -> str:
    mapping = {
        "word": "word",
        "markdown": "md",
        "excel": "excel",
        "json": "json",
        "csv": "csv",
        "parquet": "parquet",
        "pdf": "pdf",
        "txt": "txt",
        "html": "html",
        "ppt": "ppt",
    }
    if value is None:
        return "unknown"
    name = getFormatTypeName(value)
    return mapping.get(name.lower(), name.lower())


def build_tool_dag(flow_id: str, job_name: str, task_params: dict[str, Any]) -> list[dict[str, Any]]:
    template_name = build_container_template_name(flow_id)
    tool_name = task_params.get("tool_name") or task_params.get("config", {}).get("name") or job_name
    pull_params = {**task_params, "task_stage": "pull_data"}
    execute_params = {**task_params, "task_stage": "tool_execute", "tool_name": tool_name, "input_source_task": "pull_data"}
    upload_params = {**task_params, "task_stage": "upload_data", "upload_source_task": tool_name}
    return [
        _build_dag_task(flow_id=flow_id, sequence=1, task_name="pull_data", task_type="pull_data", task_params=pull_params, template_name=template_name),
        _build_dag_task(flow_id=flow_id, sequence=2, task_name=tool_name, task_type="tool_execute", task_params=execute_params, dep_sequences=[1], template_name=template_name),
        _build_dag_task(flow_id=flow_id, sequence=3, task_name="upload_data", task_type="upload_data", task_params=upload_params, dep_sequences=[2], template_name=template_name),
    ]


def build_pipeline_dag(flow_id: str, task_params: dict[str, Any]) -> list[dict[str, Any]]:
    template_name = build_container_template_name(flow_id)
    full_config = task_params.get("config") or {}
    process = full_config.get("process") or []
    base_params = split_task_params_without_config(task_params)

    dag_tasks = [
        _build_dag_task(
            flow_id=flow_id,
            sequence=1,
            task_name="pull_data",
            task_type="pull_data",
            task_params={**base_params, "task_stage": "pull_data"},
            template_name=template_name,
        )
    ]

    previous_logical = "pull_data"
    previous_sequence = 1
    sequence = 2
    for index, op in enumerate(process):
        op_name = op.get("name") or f"operator_{index + 1}"
        dag_tasks.append(_build_dag_task(
            flow_id=flow_id,
            sequence=sequence,
            task_name=op_name,
            task_type="operator_execute",
            task_params={
                **base_params,
                "task_stage": "operator_execute",
                "operator_name": op_name,
                "operator_index": index,
                "input_source_task": previous_logical,
                "config": build_per_operator_config(full_config, op),
            },
            dep_sequences=[previous_sequence],
            template_name=template_name,
        ))
        previous_logical = op_name
        previous_sequence = sequence
        sequence += 1

    dag_tasks.append(_build_dag_task(
        flow_id=flow_id,
        sequence=sequence,
        task_name="upload_data",
        task_type="upload_data",
        task_params={
            **base_params,
            "task_stage": "upload_data",
            "upload_source_task": previous_logical,
        },
        dep_sequences=[previous_sequence],
        template_name=template_name,
    ))
    return dag_tasks


def build_datasource_dag(flow_id: str, task_params: dict[str, Any]) -> list[dict[str, Any]]:
    template_name = build_container_template_name(flow_id)
    source_type = str(task_params.get("source_type_name") or task_params.get("source_type") or "unknown").lower()
    harvesting_name = source_type
    harvesting_params = {**task_params, "task_stage": "data_harvesting", "source_type_name": source_type}
    if source_type == "file":
        return [
            _build_dag_task(
                flow_id=flow_id,
                sequence=1,
                task_name=harvesting_name,
                task_type="data_harvesting",
                task_params=harvesting_params,
                template_name=template_name,
            )
        ]
    upload_params = {**task_params, "task_stage": "upload_data", "upload_source_task": harvesting_name}
    return [
        _build_dag_task(
            flow_id=flow_id,
            sequence=1,
            task_name=harvesting_name,
            task_type="data_harvesting",
            task_params=harvesting_params,
            template_name=template_name,
        ),
        _build_dag_task(
            flow_id=flow_id,
            sequence=2,
            task_name="upload_data",
            task_type="upload_data",
            task_params=upload_params,
            dep_sequences=[1],
            template_name=template_name,
        ),
    ]


def build_formatify_dag(flow_id: str, task_params: dict[str, Any]) -> list[dict[str, Any]]:
    template_name = build_container_template_name(flow_id)
    from_name = _format_short_name(task_params.get("from_data_type"))
    to_name = _format_short_name(task_params.get("to_data_type"))
    conversion_name = f"format_conversion_{from_name}2{to_name}"
    pull_params = {**task_params, "task_stage": "pull_data"}
    conversion_params = {**task_params, "task_stage": "format_conversion", "conversion_name": conversion_name, "input_source_task": "pull_data"}
    upload_params = {**task_params, "task_stage": "upload_data", "upload_source_task": conversion_name}
    return [
        _build_dag_task(flow_id=flow_id, sequence=1, task_name="pull_data", task_type="pull_data", task_params=pull_params, template_name=template_name),
        _build_dag_task(
            flow_id=flow_id,
            sequence=2,
            task_name=conversion_name,
            task_type="format_conversion",
            task_params=conversion_params,
            dep_sequences=[1],
            template_name=template_name,
        ),
        _build_dag_task(
            flow_id=flow_id,
            sequence=3,
            task_name="upload_data",
            task_type="upload_data",
            task_params=upload_params,
            dep_sequences=[2],
            template_name=template_name,
        ),
    ]
