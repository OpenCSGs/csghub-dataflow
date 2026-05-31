import json
import os
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from data_server.datasource.DatasourceModels import CollectionTask, DataSourceTaskStatusEnum
from data_server.formatify.FormatifyModels import DataFormatTask, DataFormatTaskStatusEnum
from data_server.job.JobModels import Job
from data_server.job.SubTaskManager import sync_subtasks_status
from data_server.schemas.responses import JOB_STATUS
from data_server.utils.csghub_client import (
    fetch_platform_job_status,
    parse_platform_dag_tasks,
    query_job_subtasks_status_from_csghub,
    resolve_csghub_remote_job_id,
    _ensure_bearer_authorization,
)


RUNNING_STATUSES = {
    "SUBMITTED",
    "PENDING",
    "QUEUED",
    "WAITING",
    "RUNNING",
    "PROCESSING",
    "EXECUTING",
    "IN_PROGRESS",
}
SUCCESS_STATUSES = {
    "SUCCESS",
    "SUCCEEDED",
    "COMPLETED",
    "FINISHED",
    "DONE",
}
FAILED_STATUSES = {
    "FAILED",
    "FAIL",
    "ERROR",
}
CANCELED_STATUSES = {
    "CANCELED",
    "CANCELLED",
    "STOPPED",
    "TERMINATED",
}
TIMEOUT_STATUSES = {
    "TIMEOUT",
    "TIMED_OUT",
}
TERMINAL_STATUSES = SUCCESS_STATUSES | FAILED_STATUSES | CANCELED_STATUSES | TIMEOUT_STATUSES
SUBTASK_SYNC_TRIGGER_STATUSES = SUCCESS_STATUSES | FAILED_STATUSES

# Local terminal states: completed/failed/canceled/timeout — detail page skips CSGHub fetch
COLLECTION_TERMINAL_TASK_STATUSES = frozenset({
    DataSourceTaskStatusEnum.COMPLETED.value,  # completed
    DataSourceTaskStatusEnum.ERROR.value,     # failed
    DataSourceTaskStatusEnum.STOP.value,      # canceled/stopped
})
FORMATIFY_TERMINAL_TASK_STATUSES = frozenset({
    DataFormatTaskStatusEnum.COMPLETED.value,
    DataFormatTaskStatusEnum.ERROR.value,
    DataFormatTaskStatusEnum.STOP.value,
})
JOB_TERMINAL_STATUSES = frozenset({
    JOB_STATUS.FINISHED.value,   # completed
    JOB_STATUS.FAILED.value,     # failed
    JOB_STATUS.CANCELED.value,   # canceled
    JOB_STATUS.TIMEOUT.value,    # timeout (terminal)
})

# Local non-terminal: Queued, Processing; collection/formatify WAITING, EXECUTING


def is_collection_task_locally_terminal(task_status: int | None) -> bool:
    return task_status in COLLECTION_TERMINAL_TASK_STATUSES


def is_formatify_task_locally_terminal(task_status: int | None) -> bool:
    return task_status in FORMATIFY_TERMINAL_TASK_STATUSES


def is_job_locally_terminal(status: str | None) -> bool:
    return str(status or "").strip() in JOB_TERMINAL_STATUSES


def _is_entity_locally_terminal(entity_type: str, entity) -> bool:
    if entity is None:
        return False
    if entity_type == "datasource":
        return is_collection_task_locally_terminal(getattr(entity, "task_status", None))
    if entity_type == "formatify":
        return is_formatify_task_locally_terminal(getattr(entity, "task_status", None))
    if entity_type == "job":
        return is_job_locally_terminal(getattr(entity, "status", None))
    return False


def _get_status_sync_min_age_minutes() -> int:
    try:
        return max(0, int(os.getenv("CSGHUB_STATUS_SYNC_MIN_AGE_MINUTES", "30")))
    except ValueError:
        return 30


def _entity_created_at(entity) -> datetime | None:
    created_at = getattr(entity, "created_at", None) or getattr(entity, "date_posted", None)
    if created_at is None:
        return None
    if getattr(created_at, "tzinfo", None) is not None:
        return created_at.replace(tzinfo=None)
    return created_at


def is_entity_old_enough_for_csghub_status_sync(entity) -> bool:
    """
    Do not query CSGHub until entity age exceeds CSGHUB_STATUS_SYNC_MIN_AGE_MINUTES (default 30).
    New task status is written back via Pod workflow sync; avoids immediate remote query after submit.
    """
    min_age_minutes = _get_status_sync_min_age_minutes()
    if min_age_minutes <= 0:
        return True
    created_at = _entity_created_at(entity)
    if created_at is None:
        return True
    return datetime.now() >= created_at + timedelta(minutes=min_age_minutes)


def should_query_csghub_status(entity, entity_type: str) -> bool:
    """
    Whether detail page should fetch status from CSGHub (when sync_status=true).

    Only when all of:
    - Submitted to CSGHub (has flow_id / csghub_job_id)
    - Local status still **non-terminal** (Queued/Processing or WAITING/EXECUTING)
    - Created more than CSGHUB_STATUS_SYNC_MIN_AGE_MINUTES ago (default 30 minutes)

    Skip fetch if locally terminal (Finished/COMPLETED, Failed/ERROR, Canceled/STOP, timeout).
    Do not call from list APIs.
    """
    if entity is None:
        return False
    if not (getattr(entity, "flow_id", None) or getattr(entity, "csghub_job_id", None)):
        return False
    # completed/failed/canceled/timeout are terminal; skip
    if _is_entity_locally_terminal(entity_type, entity):
        return False
    if not is_entity_old_enough_for_csghub_status_sync(entity):
        return False
    return True


def normalize_csghub_status(status: str | None) -> str:
    return str(status or "").strip()


def _status_key(status: str | None) -> str:
    return normalize_csghub_status(status).replace("-", "_").replace(" ", "_").upper()


def _map_job_status(status: str | None) -> str | None:
    status_key = _status_key(status)
    if status_key in RUNNING_STATUSES:
        if status_key in {"SUBMITTED", "PENDING", "QUEUED", "WAITING"}:
            return JOB_STATUS.QUEUED.value
        return JOB_STATUS.PROCESSING.value
    if status_key in SUCCESS_STATUSES:
        return JOB_STATUS.FINISHED.value
    if status_key in FAILED_STATUSES:
        return JOB_STATUS.FAILED.value
    if status_key in CANCELED_STATUSES:
        return JOB_STATUS.CANCELED.value
    if status_key in TIMEOUT_STATUSES:
        return JOB_STATUS.TIMEOUT.value
    return None


def _map_collection_status(status: str | None) -> int | None:
    status_key = _status_key(status)
    if status_key in RUNNING_STATUSES:
        if status_key in {"SUBMITTED", "PENDING", "QUEUED", "WAITING"}:
            return DataSourceTaskStatusEnum.WAITING.value
        return DataSourceTaskStatusEnum.EXECUTING.value
    if status_key in SUCCESS_STATUSES:
        return DataSourceTaskStatusEnum.COMPLETED.value
    if status_key in FAILED_STATUSES or status_key in TIMEOUT_STATUSES:
        return DataSourceTaskStatusEnum.ERROR.value
    if status_key in CANCELED_STATUSES:
        return DataSourceTaskStatusEnum.STOP.value
    return None


def _map_formatify_status(status: str | None) -> int | None:
    status_key = _status_key(status)
    if status_key in RUNNING_STATUSES:
        if status_key in {"SUBMITTED", "PENDING", "QUEUED", "WAITING"}:
            return DataFormatTaskStatusEnum.WAITING.value
        return DataFormatTaskStatusEnum.EXECUTING.value
    if status_key in SUCCESS_STATUSES:
        return DataFormatTaskStatusEnum.COMPLETED.value
    if status_key in FAILED_STATUSES or status_key in TIMEOUT_STATUSES:
        return DataFormatTaskStatusEnum.ERROR.value
    if status_key in CANCELED_STATUSES:
        return DataFormatTaskStatusEnum.STOP.value
    return None


def _append_callback_payload(existing_payload: str | None, callback_payload: dict | None) -> str | None:
    if callback_payload is None:
        return existing_payload

    parsed_payload = None
    if existing_payload:
        try:
            parsed_payload = json.loads(existing_payload)
        except Exception:
            parsed_payload = {"create_response_raw": existing_payload}

    if parsed_payload is None:
        parsed_payload = {}
    if not isinstance(parsed_payload, dict):
        parsed_payload = {"create_response": parsed_payload}

    history = parsed_payload.get("callback_history")
    if not isinstance(history, list):
        history = []
    history.append({
        "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "payload": callback_payload,
    })
    parsed_payload["callback_history"] = history[-20:]
    return json.dumps(parsed_payload, ensure_ascii=False)


def _should_sync_subtasks(status: str | None) -> bool:
    return _status_key(status) in SUBTASK_SYNC_TRIGGER_STATUSES


def _entity_namespace_uuid(entity) -> str | None:
    namespace = getattr(entity, "namespace_uuid", None)
    if namespace is None:
        return None
    text = str(namespace).strip()
    return text or None


def _extract_subtask_items_from_callback(callback_payload: Any) -> list[dict]:
    """Extract subtask list from platform GET or callback payload (prefer dag_tasks)."""
    if callback_payload is None:
        return []
    payload = callback_payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return []
    if not isinstance(payload, dict):
        return []

    nested = payload.get("data")
    body: dict[str, Any] = {**payload, **nested} if isinstance(nested, dict) else payload
    dag_items = parse_platform_dag_tasks(body.get("dag_tasks"))
    if dag_items:
        normalized = []
        for item in dag_items:
            normalized.append({
                **item,
                "status": _normalize_subtask_status(item.get("status")),
            })
        return normalized
    return _extract_subtask_items(payload)


def _extract_subtask_items(response: dict | list) -> list[dict]:
    if isinstance(response, list):
        return [item for item in response if isinstance(item, dict)]
    if not isinstance(response, dict):
        return []

    candidates = [
        response.get("job_subtasks"),
        response.get("subtasks"),
        response.get("items"),
        response.get("data"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            nested = (
                candidate.get("job_subtasks")
                or candidate.get("subtasks")
                or candidate.get("items")
            )
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def _normalize_subtask_status(status: str | None) -> str | None:
    status_key = _status_key(status)
    if not status_key:
        return None
    if status_key in {"SUBMITTED", "PENDING", "QUEUED", "WAITING"}:
        return "Pending"
    if status_key in RUNNING_STATUSES:
        return "Running"
    if status_key in SUCCESS_STATUSES:
        return "Finished"
    if status_key in FAILED_STATUSES or status_key in TIMEOUT_STATUSES:
        return "Failed"
    if status_key in CANCELED_STATUSES:
        return "Stopped"
    return normalize_csghub_status(status)


def _sync_subtasks_from_items(
    session: Session,
    *,
    flow_id: str | None,
    subtask_items: list[dict],
) -> dict | None:
    if not flow_id or not subtask_items:
        return None
    return sync_subtasks_status(
        session,
        flow_id=str(flow_id),
        subtask_items=subtask_items,
    )


def sync_csghub_subtasks_status_by_query(
    session: Session,
    *,
    flow_id: str | None,
    csghub_job_id: str | None,
    user_token: str | None = None,
    authorization: str | None = None,
) -> dict:
    response = query_job_subtasks_status_from_csghub(
        flow_id=flow_id,
        csghub_job_id=csghub_job_id,
        user_token=user_token,
        authorization=authorization,
    )
    subtask_items = _extract_subtask_items(response)
    if not subtask_items:
        raise ValueError("CSGHub 子任务状态查询响应中缺少 subtasks/job_subtasks/items/data 列表")

    normalized_items = []
    for item in subtask_items:
        normalized_items.append({
            **item,
            "status": _normalize_subtask_status(
                item.get("status") or item.get("state") or item.get("phase")
            ),
        })

    result = sync_subtasks_status(
        session,
        flow_id=flow_id or response.get("flow_id"),
        subtask_items=normalized_items,
    )
    result["query_response"] = response
    return result


def _find_target(session: Session, flow_id: str | None, csghub_job_id: str | None):
    if flow_id:
        if flow_id.startswith("AA"):
            task = session.query(CollectionTask).filter(CollectionTask.flow_id == flow_id).first()
            return "datasource", task
        if flow_id.startswith("AB"):
            task = session.query(DataFormatTask).filter(DataFormatTask.flow_id == flow_id).first()
            return "formatify", task
        if flow_id.startswith("AC") or flow_id.startswith("AD"):
            task = session.query(Job).filter(Job.flow_id == flow_id).first()
            return "job", task

    if csghub_job_id:
        task = session.query(CollectionTask).filter(CollectionTask.csghub_job_id == csghub_job_id).first()
        if task is not None:
            return "datasource", task
        task = session.query(DataFormatTask).filter(DataFormatTask.csghub_job_id == csghub_job_id).first()
        if task is not None:
            return "formatify", task
        task = session.query(Job).filter(Job.csghub_job_id == csghub_job_id).first()
        if task is not None:
            return "job", task

    return None, None


def sync_csghub_main_task_status(
    session: Session,
    *,
    flow_id: str | None,
    csghub_job_id: str | None,
    status: str,
    callback_payload: dict | None = None,
    user_token: str | None = None,
    authorization: str | None = None,
) -> dict:
    if not flow_id and not csghub_job_id:
        raise ValueError("flow_id 和 csghub_job_id 不能同时为空")
    if not normalize_csghub_status(status):
        raise ValueError("status 不能为空")

    entity_type, entity = _find_target(session, flow_id, csghub_job_id)
    if entity is None:
        raise ValueError("未找到匹配的主任务记录")

    current_status = normalize_csghub_status(status)
    now = datetime.now()

    entity.csghub_status = current_status
    if hasattr(entity, "csghub_response_payload"):
        entity.csghub_response_payload = _append_callback_payload(
            getattr(entity, "csghub_response_payload", None),
            callback_payload,
        )

    if entity_type == "job":
        mapped_status = _map_job_status(current_status)
        if mapped_status:
            entity.status = mapped_status
            if _status_key(current_status) in TERMINAL_STATUSES:
                entity.date_finish = now
    elif entity_type == "datasource":
        mapped_status = _map_collection_status(current_status)
        if mapped_status is not None:
            entity.task_status = mapped_status
            if mapped_status == DataSourceTaskStatusEnum.EXECUTING.value and entity.start_run_at is None:
                entity.start_run_at = now
            if _status_key(current_status) in TERMINAL_STATUSES:
                entity.end_run_at = now
    elif entity_type == "formatify":
        mapped_status = _map_formatify_status(current_status)
        if mapped_status is not None:
            entity.task_status = mapped_status
            if mapped_status == DataFormatTaskStatusEnum.EXECUTING.value and entity.start_run_at is None:
                entity.start_run_at = now
            if _status_key(current_status) in TERMINAL_STATUSES:
                entity.end_run_at = now
    else:
        raise ValueError(f"不支持的主任务类型: {entity_type}")

    subtask_sync_result = None
    subtask_sync_error = None
    flow_id = getattr(entity, "flow_id", None)
    subtask_items = _extract_subtask_items_from_callback(callback_payload)
    if subtask_items and flow_id:
        try:
            subtask_sync_result = _sync_subtasks_from_items(
                session,
                flow_id=flow_id,
                subtask_items=subtask_items,
            )
        except Exception as exc:
            subtask_sync_error = str(exc)
    elif _should_sync_subtasks(current_status):
        try:
            subtask_sync_result = sync_csghub_subtasks_status_by_query(
                session,
                flow_id=flow_id,
                csghub_job_id=getattr(entity, "csghub_job_id", None),
                user_token=user_token,
                authorization=authorization,
            )
        except Exception as exc:
            subtask_sync_error = str(exc)

    session.commit()
    result = {
        "entity_type": entity_type,
        "id": getattr(entity, "id", getattr(entity, "job_id", None)),
        "flow_id": getattr(entity, "flow_id", None),
        "csghub_job_id": getattr(entity, "csghub_job_id", None),
        "csghub_status": getattr(entity, "csghub_status", None),
    }
    if subtask_sync_result is not None:
        result["subtask_sync"] = subtask_sync_result
    if subtask_sync_error is not None:
        result["subtask_sync_error"] = subtask_sync_error
    return result


def sync_csghub_main_task_status_by_query(
    session: Session,
    *,
    flow_id: str | None,
    csghub_job_id: str | None,
    user_token: str | None = None,
    authorization: str | None = None,
    csghub_response_payload: Any = None,
) -> dict:
    entity_type, entity = _find_target(session, flow_id, csghub_job_id)
    if entity is not None and _is_entity_locally_terminal(entity_type, entity):
        return {
            "skipped": True,
            "reason": "local_terminal_status",  # local terminal (completed/failed/canceled/timeout)
            "entity_type": entity_type,
            "id": getattr(entity, "id", getattr(entity, "job_id", None)),
            "flow_id": getattr(entity, "flow_id", flow_id),
        }
    if entity is not None and not is_entity_old_enough_for_csghub_status_sync(entity):
        return {
            "skipped": True,
            "reason": "created_too_recent",
            "entity_type": entity_type,
            "id": getattr(entity, "id", getattr(entity, "job_id", None)),
            "flow_id": getattr(entity, "flow_id", flow_id),
            "min_age_minutes": _get_status_sync_min_age_minutes(),
        }

    namespace = _entity_namespace_uuid(entity) if entity is not None else None
    if not namespace:
        raise ValueError("任务缺少 namespace_uuid，无法查询 CSGHub platform 任务状态")
    if not _ensure_bearer_authorization(authorization):
        raise ValueError("查询任务状态需要请求头 Authorization: Bearer")

    parsed = fetch_platform_job_status(
        namespace=namespace,
        csghub_job_id=csghub_job_id or getattr(entity, "csghub_job_id", None),
        flow_id=flow_id or getattr(entity, "flow_id", None),
        authorization=authorization,
        csghub_response_payload=csghub_response_payload
        or getattr(entity, "csghub_response_payload", None),
    )
    response = parsed.get("raw_response") or {}
    status = parsed["status"]
    resolved_job_id = (
        parsed.get("csghub_job_id")
        or parsed.get("argo_task_id")
        or resolve_csghub_remote_job_id(
            csghub_job_id or getattr(entity, "csghub_job_id", None),
            flow_id=flow_id or getattr(entity, "flow_id", None),
            csghub_response_payload=csghub_response_payload
            or getattr(entity, "csghub_response_payload", None),
        )
    )

    result = sync_csghub_main_task_status(
        session,
        flow_id=flow_id or getattr(entity, "flow_id", None),
        csghub_job_id=resolved_job_id,
        status=status,
        callback_payload=response,
        user_token=user_token,
        authorization=authorization,
    )
    result["query_response"] = response
    result["query_source"] = "platform"
    result["subtask_count"] = len(parsed.get("subtask_items") or [])
    return result
