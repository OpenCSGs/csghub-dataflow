"""Argo Pod syncs output/trace to DataFlow API using legacy naming."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from loguru import logger

from data_server.pod.http_retry_client import post_json_with_retry
from data_server.utils.csghub_client import _build_api_jwt_headers, get_dataflow_trace_sync_url
from data_server.utils.trace_filenames import is_legacy_trace_filename


def get_trace_sync_url() -> str:
    return get_dataflow_trace_sync_url()


def _read_trace_file(path: Path) -> dict[str, Any]:
    """Return jsonl/txt as UTF-8 text, consistent with read_jsonl_to_list."""
    name = path.name
    if path.suffix.lower() in {".jsonl", ".txt", ".log", ".yaml", ".yml", ".json"}:
        return {"name": name, "content": path.read_text(encoding="utf-8")}
    raw = path.read_bytes()
    import base64

    return {"name": name, "content_base64": base64.b64encode(raw).decode("ascii")}


def collect_trace_payload(
    *,
    flow_id: str,
    trace_dir: str,
    operator_name: str,
    job_id: int | None = None,
    operator_index: int | None = None,
) -> dict[str, Any]:
    """
    Collect trace files for current operator only (legacy Tracer naming); do not sync single-operator config.yaml,
    to avoid overwriting full pipeline config written at task creation.
    """
    if not operator_name:
        raise ValueError("operator_name is required for trace sync")

    files: list[dict[str, Any]] = []
    trace_path = Path(trace_dir)
    if trace_path.is_dir():
        for entry in sorted(trace_path.iterdir()):
            if not entry.is_file():
                continue
            if not is_legacy_trace_filename(entry.name, operator_name):
                continue
            try:
                files.append(_read_trace_file(entry))
            except Exception as exc:
                logger.warning("Skip trace file {}: {}", entry, exc)

    payload: dict[str, Any] = {
        "flow_id": flow_id,
        "operator_name": operator_name,
        "sync_mode": "trace_only",
        "files": files,
    }
    if job_id is not None:
        payload["job_id"] = job_id
    if operator_index is not None:
        payload["operator_index"] = operator_index
    return payload


def push_trace_to_dataflow_api(
    payload: dict[str, Any],
    *,
    authorization: str | None,
) -> dict[str, Any]:
    if not authorization or not str(authorization).strip():
        raise ValueError("authorization (JWT) is required for trace sync")

    url = get_trace_sync_url()
    headers = _build_api_jwt_headers(authorization)
    internal_token = (
        os.getenv("DATAFLOW_INTERNAL_TOKEN", "").strip()
        or os.getenv("CSGHUB_DATAFLOW_CALLBACK_TOKEN", "").strip()
    )
    if internal_token:
        headers["X-Dataflow-Internal-Token"] = internal_token

    timeout = int(os.getenv("CSGHUB_HTTP_TIMEOUT", "30") or "30")
    parsed = post_json_with_retry(
        url=url,
        payload=payload,
        headers=headers,
        timeout=timeout,
        label="trace sync",
    )
    logger.info(
        "Trace synced | url={} | flow_id={} | operator={} | files={}",
        url,
        payload.get("flow_id"),
        payload.get("operator_name"),
        [f.get("name") for f in (payload.get("files") or [])],
    )
    return parsed


def sync_output_trace(
    *,
    flow_id: str,
    output_dir: str,
    operator_name: str,
    authorization: str | None,
    job_id: int | None = None,
    operator_index: int | None = None,
) -> bool:
    trace_dir = os.path.join(output_dir, "trace")
    if not operator_name:
        logger.warning("sync_output_trace skipped: missing operator_name flow_id={}", flow_id)
        return False
    if not authorization or not str(authorization).strip():
        logger.warning(
            "sync_output_trace skipped: missing authorization (JWT) flow_id={} operator={}",
            flow_id,
            operator_name,
        )
        return False
    if not os.path.isdir(trace_dir):
        logger.debug("No trace dir for flow_id={} operator={}", flow_id, operator_name)
        return False

    try:
        payload = collect_trace_payload(
            flow_id=flow_id,
            trace_dir=trace_dir,
            operator_name=operator_name,
            job_id=job_id,
            operator_index=operator_index,
        )
        if not payload.get("files"):
            logger.debug(
                "No trace files to sync flow_id={} operator={}",
                flow_id,
                operator_name,
            )
            return False
        push_trace_to_dataflow_api(payload, authorization=authorization)
        return True
    except Exception as exc:
        logger.warning(
            "sync_output_trace failed flow_id={} operator={}: {}",
            flow_id,
            operator_name,
            exc,
        )
        return False
