"""Pod workflow step sync: main/subtask status and upload branch (data flow)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from data_server.datasource.DatasourceModels import DataSourceTaskStatusEnum
from data_server.formatify.FormatifyModels import DataFormatTaskStatusEnum
from data_server.job.SubTaskManager import (
    _parse_datetime,
    sync_subtasks_status,
    update_subtask_status,
)
from data_server.job.SubTaskModels import JobSubTask
from data_server.schemas.responses import JOB_STATUS
from data_server.utils.csghub_status_sync import (
    TERMINAL_STATUSES,
    _append_callback_payload,
    _find_target,
    _map_collection_status,
    _map_formatify_status,
    _map_job_status,
    _status_key,
    normalize_csghub_status,
)

WORKFLOW_EVENTS = frozenset({
    "step_started",
    "step_finished",
    "step_failed",
    "workflow_finished",
})


def resolve_entity_by_flow_id(session: Session, flow_id: str, job_id: int | None = None):
    entity_type, entity = _find_target(session, flow_id, None)
    if entity is None:
        raise ValueError(f"未找到 flow_id={flow_id} 对应的任务")
    if job_id is not None and entity_type == "job":
        if getattr(entity, "job_id", None) != job_id:
            raise ValueError(f"job_id={job_id} 与 flow_id={flow_id} 不匹配")
    return entity_type, entity


def _parse_dt(value) -> datetime | None:
    return _parse_datetime(value)


def _parse_extra_config_dict(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _apply_upload_fields(entity_type: str, entity, upload: dict | None) -> dict[str, Any]:
    if not upload:
        return {}
    repo_id = str(upload.get("repo_id") or upload.get("upload_repo_id") or "").strip()
    branch = str(upload.get("branch") or upload.get("upload_branch") or "").strip()
    if not branch:
        return {}
    applied: dict[str, Any] = {"repo_id": repo_id or None, "branch": branch}
    if entity_type == "datasource":
        entity.csg_hub_server_branch = branch
        applied["csg_hub_server_branch"] = branch
    elif entity_type == "formatify":
        entity.to_csg_hub_dataset_default_branch = branch
        applied["to_csg_hub_dataset_default_branch"] = branch
    elif entity_type == "job":
        entity.export_branch_name = branch
        applied["export_branch_name"] = branch
        if repo_id:
            entity.export_repo_id = repo_id
            applied["export_repo_id"] = repo_id
    return applied


def _find_subtask(session: Session, flow_id: str, current: dict) -> JobSubTask | None:
    task_id = current.get("task_id") or current.get("argo_dag_task_id")
    task_name = current.get("task_name") or current.get("name")
    if task_id:
        row = session.query(JobSubTask).filter(
            JobSubTask.flow_id == flow_id,
            JobSubTask.task_id == str(task_id),
        ).first()
        if row:
            return row
    if task_name:
        return session.query(JobSubTask).filter(
            JobSubTask.flow_id == flow_id,
            JobSubTask.task_name == str(task_name),
        ).first()
    return None


def _apply_current_subtask(
    session: Session,
    *,
    flow_id: str,
    current: dict | None,
    event: str,
    finalize: bool,
    message: str | None = None,
) -> dict[str, Any]:
    if not current:
        return {"updated": 0}

    subtask = _find_subtask(session, flow_id, current)
    if subtask is None:
        logger.warning(
            "workflow sync: subtask not found flow_id={} task_name={} task_id={}",
            flow_id,
            current.get("task_name"),
            current.get("task_id"),
        )
        return {"updated": 0, "skipped": True}

    status = current.get("status")
    if not status:
        if event == "step_started":
            status = "Running"
        elif event == "step_failed":
            status = "Failed"
        else:
            status = "Finished"

    started_at = _parse_dt(
        current.get("started_at") or current.get("start_time")
    )
    finished_at = _parse_dt(
        current.get("finished_at") or current.get("finish_time")
    )
    if event == "step_started" and started_at is None:
        started_at = datetime.now()
    if event in {"step_finished", "step_failed", "workflow_finished"} and finished_at is None:
        finished_at = datetime.now()

    error_message = current.get("error_message") or message
    update_subtask_status(
        session,
        flow_id=flow_id,
        task_name=subtask.task_name,
        status=str(status),
        error_message=error_message,
        started_at=started_at,
        finished_at=finished_at,
    )

    finalized_prior = 0
    if finalize and event in {"step_finished", "workflow_finished"} and _status_key(status) in {
        "FINISHED", "SUCCEEDED", "SUCCESS", "COMPLETED", "DONE",
    }:
        prior = session.query(JobSubTask).filter(
            JobSubTask.flow_id == flow_id,
            JobSubTask.task_sequence <= subtask.task_sequence,
            JobSubTask.id != subtask.id,
        ).all()
        now = finished_at or datetime.now()
        for row in prior:
            if str(row.status or "").strip() not in {"Finished", "Failed", "Stopped"}:
                row.status = "Finished"
                if row.finished_at is None:
                    row.finished_at = now
                finalized_prior += 1

    return {
        "task_name": subtask.task_name,
        "status": status,
        "updated": 1,
        "finalized_prior": finalized_prior,
    }


def _apply_main_task(
    entity_type: str,
    entity,
    *,
    event: str,
    main: dict | None,
    finalize: bool,
    message: str | None = None,
) -> dict[str, Any]:
    main = main or {}
    status_raw = main.get("status") or main.get("csghub_status")
    if not status_raw and event == "step_started":
        status_raw = "Running"
    elif not status_raw and event == "step_failed":
        status_raw = "Failed"
    elif not status_raw and event == "workflow_finished":
        status_raw = "Succeeded"
    # step_finished does not set main terminal status; step_failed marks main failed (operator Pod failure, etc.)

    result: dict[str, Any] = {}
    if status_raw:
        current_status = normalize_csghub_status(status_raw)
        entity.csghub_status = current_status
        result["csghub_status"] = current_status

        started_at = _parse_dt(main.get("started_at"))
        finished_at = _parse_dt(main.get("finished_at"))

        if entity_type == "job":
            mapped = _map_job_status(current_status)
            if mapped:
                entity.status = mapped
                result["status"] = mapped
            elif event == "step_failed" and _status_key(current_status) in {
                "FAILED",
                "FAILURE",
                "ERROR",
            }:
                entity.status = JOB_STATUS.FAILED.value
                result["status"] = entity.status
            if _status_key(current_status) in TERMINAL_STATUSES and event in {
                "workflow_finished",
                "step_failed",
            }:
                entity.date_finish = finished_at or datetime.now()
                result["date_finish"] = entity.date_finish
        elif entity_type == "datasource":
            mapped = _map_collection_status(current_status)
            if mapped is not None:
                entity.task_status = mapped
                result["task_status"] = mapped
            if event == "step_started" or mapped == DataSourceTaskStatusEnum.EXECUTING.value:
                if started_at is not None:
                    entity.start_run_at = started_at
                elif entity.start_run_at is None and event == "step_started":
                    entity.start_run_at = datetime.now()
            if event in {"workflow_finished", "step_failed"} or (
                finalize and _status_key(current_status) in TERMINAL_STATUSES
            ):
                if finished_at is not None:
                    entity.end_run_at = finished_at
                else:
                    entity.end_run_at = datetime.now()
        elif entity_type == "formatify":
            mapped = _map_formatify_status(current_status)
            if mapped is not None:
                entity.task_status = mapped
                result["task_status"] = mapped
            if event == "step_started" or mapped == DataFormatTaskStatusEnum.EXECUTING.value:
                if started_at is not None:
                    entity.start_run_at = started_at
                elif entity.start_run_at is None and event == "step_started":
                    entity.start_run_at = datetime.now()
            if event in {"workflow_finished", "step_failed"} or (
                finalize and _status_key(current_status) in TERMINAL_STATUSES
            ):
                if finished_at is not None:
                    entity.end_run_at = finished_at
                else:
                    entity.end_run_at = datetime.now()

    if entity_type == "datasource":
        records_count = main.get("records_count")
        total_count = main.get("total_count")
        if records_count is not None:
            try:
                entity.records_count = int(records_count)
                result["records_count"] = entity.records_count
            except (TypeError, ValueError):
                pass
        if total_count is not None:
            try:
                entity.total_count = int(total_count)
                result["total_count"] = entity.total_count
            except (TypeError, ValueError):
                pass

    if entity_type == "job":
        for field in ("data_count", "process_count"):
            value = main.get(field)
            if value is None:
                continue
            try:
                setattr(entity, field, int(value))
                result[field] = getattr(entity, field)
            except (TypeError, ValueError):
                pass

    if message and hasattr(entity, "csghub_response_payload"):
        entity.csghub_response_payload = _append_callback_payload(
            getattr(entity, "csghub_response_payload", None),
            {"workflow_sync_message": message, "event": event},
        )

    return result


def apply_workflow_sync(
    session: Session,
    *,
    flow_id: str,
    event: str,
    job_id: int | None = None,
    finalize: bool = False,
    main: dict | None = None,
    current_subtask: dict | None = None,
    subtasks: list[dict] | None = None,
    upload: dict | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    event = str(event or "").strip()
    if event not in WORKFLOW_EVENTS:
        raise ValueError(f"不支持的 event: {event}")

    entity_type, entity = resolve_entity_by_flow_id(session, flow_id, job_id=job_id)

    subtask_result: dict[str, Any] = {}
    if subtasks:
        subtask_result = sync_subtasks_status(session, flow_id=flow_id, subtask_items=subtasks)
    elif current_subtask:
        subtask_result = _apply_current_subtask(
            session,
            flow_id=flow_id,
            current=current_subtask,
            event=event,
            finalize=finalize,
            message=message,
        )

    main_result = _apply_main_task(
        entity_type,
        entity,
        event=event,
        main=main,
        finalize=finalize,
        message=message,
    )

    upload_applied: dict[str, Any] = {}
    if upload and event == "workflow_finished":
        status_key = _status_key((main or {}).get("status") or "Succeeded")
        if status_key in {"SUCCEEDED", "SUCCESS", "COMPLETED", "FINISHED", "DONE"}:
            upload_applied = _apply_upload_fields(entity_type, entity, upload)

    session.commit()

    return {
        "entity_type": entity_type,
        "id": getattr(entity, "id", getattr(entity, "job_id", None)),
        "flow_id": getattr(entity, "flow_id", flow_id),
        "event": event,
        "finalize": finalize,
        "main": main_result,
        "subtask": subtask_result,
        "upload": upload_applied,
    }


def collection_task_export_aliases(collection_task) -> dict[str, str | None]:
    """Align collection list fields with operator task list."""
    export_repo_id = None
    export_branch_name = collection_task.csg_hub_server_branch
    datasource = getattr(collection_task, "datasource", None)
    if datasource is not None:
        extra = _parse_extra_config_dict(datasource.extra_config)
        export_repo_id = extra.get("csg_hub_dataset_id")
        if not export_branch_name:
            export_branch_name = (
                extra.get("csg_hub_dataset_default_branch")
                or extra.get("csg_hub_dataset_branch")
            )
    return {
        "export_repo_id": export_repo_id,
        "export_branch_name": export_branch_name,
    }
