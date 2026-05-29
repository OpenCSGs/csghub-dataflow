"""
Argo / CSGHub DAG naming rules (centralized to avoid platform misparsing keywords as dependencies).

Background (typical CSGHub Workflow generation behavior):
- DAG node names cannot contain '_', only [a-z0-9-] (lowercase required for Pod RFC1123 names)
- Node names / task_type with semantic tokens (mysql, harvesting, data, etc.) may become extra dependencies
- Business fields in task_params JSON (source_type_name, extra_config, etc.) may still trigger platform parsing

Recommended strategy (default CSGHUB_ARGO_DAG_NODE_NAMING=id):
- Argo DAG name / deps: task ID only (e.g. AA4101, AA4102), no business semantics
- parameters.task_type: short aliases (datasource / upload / pull …), not data_harvesting
- Business semantics: in task_params (current_task_name, task_stage, upload_source_task, etc.); Pod executes accordingly

Environment variables:
- CSGHUB_ARGO_DAG_NODE_NAMING=id | logical
  - id: DAG node name = task ID (recommended when many tasks or messy names)
  - logical: DAG node name = sanitized logical name (only if confirmed safe with CSGHub)
"""

from __future__ import annotations

import os
import re
from typing import Literal

# Internal task_type -> Argo/CSGHub task_type parameter (avoid data_xxx being tokenized)
ARGO_TASK_TYPE_ALIASES: dict[str, str] = {
    "data_harvesting": "datasource",
    "upload_data": "upload",
    "pull_data": "pull",
    "format_conversion": "formatify",
    "tool_execute": "tool",
    "operator_execute": "pipeline",
    "datasource": "datasource",
    "formatify": "formatify",
    "pipeline": "pipeline",
    "tool": "tool",
}

_DAG_NODE_INVALID = re.compile(r"[^a-zA-Z0-9-]+")
_DAG_NODE_MULTI_DASH = re.compile(r"-+")


def get_dag_node_naming_mode() -> Literal["id", "logical"]:
    mode = os.getenv("CSGHUB_ARGO_DAG_NODE_NAMING", "id").strip().lower()
    return "logical" if mode == "logical" else "id"


def sanitize_argo_dag_node_name(name: str, *, fallback: str = "task") -> str:
    """Convert to valid Argo/K8s name segment (lowercase, a-z0-9- only, alphanumeric ends)."""
    text = str(name or "").strip().lower().replace("_", "-")
    text = _DAG_NODE_INVALID.sub("-", text)
    text = _DAG_NODE_MULTI_DASH.sub("-", text).strip("-")
    if not text or not text[0].isalnum():
        text = fallback
    return text[:253]


def to_argo_task_type_param(logical_type: str) -> str:
    """Argo container task_type param, decoupled from Pod current_task_type."""
    key = str(logical_type or "").strip()
    if key in ARGO_TASK_TYPE_ALIASES:
        return ARGO_TASK_TYPE_ALIASES[key]
    return sanitize_argo_dag_node_name(key, fallback="step")


def resolve_dag_node_name(*, task_id: str, logical_name: str) -> str:
    """Argo node name written to dag_tasks[].name."""
    if get_dag_node_naming_mode() == "id":
        return sanitize_argo_dag_node_name(str(task_id), fallback="step")
    return sanitize_argo_dag_node_name(logical_name, fallback=sanitize_argo_dag_node_name(str(task_id)))


def make_dag_task_id(flow_id: str, sequence: int) -> str:
    """DAG task ID; matches Argo node name, lowercase."""
    return f"{flow_id[:30]}{sequence:02d}".lower()


def resolve_dag_dep_node_names(
    flow_id: str,
    dep_sequences: list[int],
    *,
    sequence_to_logical: dict[int, str] | None = None,
) -> list[str]:
    """Convert dependent step indices to Argo dependencies list."""
    names: list[str] = []
    for seq in dep_sequences:
        task_id = make_dag_task_id(flow_id, seq)
        logical = (sequence_to_logical or {}).get(seq, task_id)
        names.append(resolve_dag_node_name(task_id=task_id, logical_name=logical))
    return names
