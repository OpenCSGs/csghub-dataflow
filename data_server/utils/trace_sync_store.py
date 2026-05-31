"""Write Pod-synced trace to local machine using legacy work_dir/trace layout."""

from __future__ import annotations

import base64
import os
from typing import Any

from loguru import logger

from data_server.utils.csghub_status_sync import _find_target
from data_server.utils.job_work_dir import (
    get_local_job_work_dir,
    get_local_trace_dir,
    write_local_config_yaml,
)
from data_server.utils.trace_filenames import is_legacy_trace_filename


def _safe_filename(name: str) -> str:
    base = os.path.basename(str(name or "").strip())
    if not base or base in {".", ".."}:
        raise ValueError(f"invalid trace file name: {name!r}")
    return base


def _write_trace_file(target: str, *, content: str | None, content_base64: str | None) -> None:
    if content_base64:
        data = base64.b64decode(content_base64)
        with open(target, "wb") as f:
            f.write(data)
        return
    if content is None:
        raise ValueError(f"missing content for {target}")
    with open(target, "w", encoding="utf-8", newline="") as f:
        f.write(content)


def save_trace_files(
    *,
    flow_id: str,
    files: list[dict[str, Any]],
    operator_name: str | None = None,
    sync_mode: str = "trace_only",
    config_yaml: str | None = None,
) -> dict[str, Any]:
    """
    sync_mode:
      - trace_only (default): append/overwrite trace dir files only; do not change config.yaml
      - init_config: write only when local config.yaml is missing (task creation fallback)
    """
    if not flow_id:
        raise ValueError("flow_id is required")

    mode = (sync_mode or "trace_only").strip().lower()
    work_dir = get_local_job_work_dir(flow_id)
    trace_dir = get_local_trace_dir(flow_id)
    saved: list[str] = []
    skipped: list[str] = []

    for item in files or []:
        if not isinstance(item, dict):
            continue
        name = _safe_filename(item.get("name") or "")
        if not is_legacy_trace_filename(name, operator_name):
            skipped.append(name)
            logger.warning(
                "Skip non-legacy trace file flow_id={} name={} operator={}",
                flow_id,
                name,
                operator_name,
            )
            continue
        target = os.path.join(trace_dir, name)
        _write_trace_file(
            target,
            content=item.get("content"),
            content_base64=item.get("content_base64"),
        )
        saved.append(name)

    config_path = os.path.join(work_dir, "config.yaml")
    if config_yaml and mode == "init_config" and not os.path.isfile(config_path):
        write_local_config_yaml(flow_id, config_yaml)

    if files and not saved:
        raise ValueError(
            "无合法 trace 文件可保存（需 mapper|filter|duplicate-{op}.jsonl 或 count-{op}.txt，"
            f"且算子名与 operator_name 一致），已跳过: {skipped}"
        )

    return {
        "flow_id": flow_id,
        "work_dir": work_dir,
        "trace_dir": trace_dir,
        "saved_files": saved,
        "skipped_files": skipped,
        "sync_mode": mode,
    }


def bind_local_work_dir_for_entity(entity, flow_id: str) -> str:
    work_dir = get_local_job_work_dir(flow_id)
    if hasattr(entity, "work_dir"):
        entity.work_dir = work_dir
    return work_dir


def resolve_entity_by_flow_id(session, flow_id: str, job_id: int | None = None):
    entity_type, entity = _find_target(session, flow_id, None)
    if entity is None:
        raise ValueError(f"未找到 flow_id={flow_id} 对应的任务")
    if job_id is not None and entity_type == "job":
        if getattr(entity, "job_id", None) != job_id:
            raise ValueError(f"job_id={job_id} 与 flow_id={flow_id} 不匹配")
    return entity_type, entity
