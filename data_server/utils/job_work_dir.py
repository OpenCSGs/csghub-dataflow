"""Local work dir on DataFlow API host for CSGHub tasks (detail page trace/config)."""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger


def get_local_work_root() -> str:
    root = (
        os.getenv("DATAFLOW_LOCAL_WORK_DIR", "").strip()
        or os.getenv("DATA_DIR", "").strip()
    )
    if not root:
        try:
            from data_server.utils.project_paths import get_project_root

            root = str(get_project_root() / "runtime_jobs")
        except Exception:
            root = os.path.join(os.getcwd(), "runtime_jobs")
    return os.path.abspath(root.rstrip("/"))


def get_local_job_work_dir(flow_id: str) -> str:
    if not flow_id or not str(flow_id).strip():
        raise ValueError("flow_id is required for local job work dir")
    path = os.path.join(get_local_work_root(), "jobs", str(flow_id).strip())
    os.makedirs(path, exist_ok=True)
    return path


def get_local_trace_dir(flow_id: str) -> str:
    trace_dir = os.path.join(get_local_job_work_dir(flow_id), "trace")
    os.makedirs(trace_dir, exist_ok=True)
    return trace_dir


def write_local_config_yaml(flow_id: str, content: str) -> str:
    work_dir = get_local_job_work_dir(flow_id)
    config_path = os.path.join(work_dir, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.debug("Wrote local config.yaml for flow_id={} path={}", flow_id, config_path)
    return config_path


def init_local_job_work_dir(flow_id: str, *, config_yaml: str | None = None) -> str:
    work_dir = get_local_job_work_dir(flow_id)
    os.makedirs(os.path.join(work_dir, "trace"), exist_ok=True)
    if config_yaml:
        write_local_config_yaml(flow_id, config_yaml)
    return work_dir
