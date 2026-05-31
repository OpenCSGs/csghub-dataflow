"""Argo Pod syncs step status and terminal upload branch to DataFlow API."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from data_server.pod.http_retry_client import post_json_with_retry
from data_server.utils.csghub_client import (
    _build_api_jwt_headers,
    get_dataflow_workflow_sync_url,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def build_current_subtask_payload(task_params: dict, *, status: str | None = None) -> dict[str, Any]:
    """Align with job_subtasks.task_name / task_id (logical_name, argo_dag_task_id in DAG)."""
    task_name = (
        task_params.get("current_task_name")
        or task_params.get("operator_name")
        or task_params.get("tool_name")
        or task_params.get("task_stage")
        or "unknown"
    )
    payload: dict[str, Any] = {
        "task_name": str(task_name),
        "task_type": task_params.get("current_task_type") or task_params.get("task_stage"),
    }
    task_id = (
        task_params.get("argo_dag_task_id")
        or task_params.get("task_id")
        or task_params.get("dag_task_id")
    )
    if task_id:
        payload["task_id"] = str(task_id)
    if status:
        payload["status"] = status
    return payload


def _resolve_pod_authorization(task_params: dict) -> str | None:
    """CSGHub task_params may lack authorization; fall back to user_token / Pod env."""
    auth = task_params.get("authorization")
    if auth and str(auth).strip():
        return str(auth).strip()
    token = task_params.get("user_token")
    if token and str(token).strip():
        return str(token).strip()
    for env_key in (
        "DATAFLOW_AUTHORIZATION",
        "USER_AUTHORIZATION",
        "CSGHUB_AUTHORIZATION",
    ):
        env_auth = os.getenv(env_key, "").strip()
        if env_auth:
            return env_auth
    return None


def _pod_internal_token_configured() -> bool:
    return bool(
        os.getenv("DATAFLOW_INTERNAL_TOKEN", "").strip()
        or os.getenv("CSGHUB_DATAFLOW_CALLBACK_TOKEN", "").strip()
    )


def is_workflow_finalize_step(task_type: str, task_params: dict) -> bool:
    normalized = str(task_type or "").strip()
    if normalized == "upload_data":
        return True
    if normalized in {"data_harvesting", "datasource"}:
        source_name = str(task_params.get("source_type_name") or "").lower()
        if source_name == "file":
            return True
        source_type = task_params.get("source_type")
        try:
            if int(source_type) == 3:
                return True
        except (TypeError, ValueError):
            pass
    return False


def push_workflow_sync(
    *,
    task_params: dict,
    event: str,
    finalize: bool = False,
    started_at: str | None = None,
    finished_at: str | None = None,
    main_status: str | None = None,
    upload: dict[str, str] | None = None,
    message: str | None = None,
    progress: dict[str, int] | None = None,
    fail_on_error: bool = False,
) -> dict[str, Any] | None:
    """
    Argo Pod only: sync write failures do not raise by default (avoid Pod false failure on workflow/sync 502);
    status can be compensated via detail page sync_status.
    """
    flow_id = task_params.get("flow_id")
    if not flow_id:
        logger.warning("push_workflow_sync skipped: missing flow_id")
        return None

    authorization = _resolve_pod_authorization(task_params)
    if not authorization and not _pod_internal_token_configured():
        logger.warning(
            "push_workflow_sync skipped: missing authorization and internal token flow_id={}",
            flow_id,
        )
        if fail_on_error:
            raise ValueError(
                "authorization (JWT) or DATAFLOW_INTERNAL_TOKEN is required for workflow sync"
            )
        return None

    current = build_current_subtask_payload(task_params)
    if event == "step_started":
        current["status"] = "Running"
        current["started_at"] = started_at or _utc_now_iso()
    elif event == "step_failed":
        current["status"] = "Failed"
        current["finished_at"] = finished_at or _utc_now_iso()
        if message:
            current["error_message"] = message
    else:
        current["status"] = "Finished"
        if started_at:
            current["started_at"] = started_at
        current["finished_at"] = finished_at or _utc_now_iso()

    main: dict[str, Any] = {}
    if main_status:
        main["status"] = main_status
        main["csghub_status"] = main_status
    if event == "step_started":
        main["started_at"] = started_at or _utc_now_iso()
    if event in {"workflow_finished", "step_failed"}:
        main["finished_at"] = finished_at or _utc_now_iso()
    if progress:
        main.update(progress)

    body: dict[str, Any] = {
        "flow_id": flow_id,
        "event": event,
        "finalize": finalize,
        "current_subtask": current,
    }
    job_id = task_params.get("job_id")
    if job_id is not None:
        body["job_id"] = job_id
    if main:
        body["main"] = main
    if upload:
        body["upload"] = upload
    if message:
        body["message"] = message

    url = get_dataflow_workflow_sync_url()
    headers = _build_api_jwt_headers(authorization)
    internal_token = (
        os.getenv("DATAFLOW_INTERNAL_TOKEN", "").strip()
        or os.getenv("CSGHUB_DATAFLOW_CALLBACK_TOKEN", "").strip()
    )
    if internal_token:
        headers["X-Dataflow-Internal-Token"] = internal_token

    timeout = int(os.getenv("CSGHUB_HTTP_TIMEOUT", "30") or "30")
    try:
        parsed = post_json_with_retry(
            url=url,
            payload=body,
            headers=headers,
            timeout=timeout,
            label="workflow sync",
        )
    except Exception as exc:
        if fail_on_error:
            raise RuntimeError(str(exc)) from exc
        logger.warning("push_workflow_sync failed flow_id={}: {}", flow_id, exc)
        return None

    logger.info(
        "Workflow synced | url={} | flow_id={} | event={} | finalize={}",
        url,
        flow_id,
        event,
        finalize,
    )
    return parsed
