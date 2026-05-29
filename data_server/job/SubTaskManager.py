import json
from datetime import datetime

from sqlalchemy.orm import Session

from data_server.job.SubTaskModels import JobSubTask
from data_server.logic.models import OperatorIdentifierItem

OPERATOR_EXECUTE_TASK_TYPE = "operator_execute"
# When writing job_subtasks, map via to_argo_task_type_param: operator_execute -> pipeline
OPERATOR_SUBTASK_TASK_TYPES = (OPERATOR_EXECUTE_TASK_TYPE, "pipeline")
NON_OPERATOR_SUBTASK_NAMES = frozenset({"pull_data", "upload_data"})


def clear_subtasks_for_parent(
    session: Session,
    *,
    parent_type: str,
    parent_id: int,
) -> None:
    """Clear pre-written subtasks when main task creation fails."""
    session.query(JobSubTask).filter(
        JobSubTask.parent_type == parent_type,
        JobSubTask.parent_id == parent_id,
    ).delete()


def replace_subtasks_for_parent(
    session: Session,
    *,
    parent_type: str,
    parent_id: int,
    flow_id: str,
    dag_tasks: list[dict],
):
    session.query(JobSubTask).filter(
        JobSubTask.parent_type == parent_type,
        JobSubTask.parent_id == parent_id,
    ).delete()

    for index, task in enumerate(dag_tasks, start=1):
        deps = task.get("deps", [])
        task_params_value = ""
        for param in _iter_task_parameters(task):
            if param.get("name") == "task_params":
                task_params_value = param.get("value", "")
                break

        session.add(JobSubTask(
            parent_type=parent_type,
            parent_id=parent_id,
            flow_id=flow_id,
            task_id=task["id"],
            task_name=task.get("logical_name") or task["name"],
            task_type=_extract_task_type(task),
            task_sequence=index,
            deps=json.dumps(deps, ensure_ascii=False),
            status="Pending",
            request_payload=task_params_value,
        ))


def _iter_task_parameters(task: dict):
    yield from task.get("parameters") or task.get("params") or []


def _extract_task_type(task: dict) -> str:
    for param in _iter_task_parameters(task):
        if param.get("name") == "task_type":
            return param.get("value", "")
    return ""


def update_subtask_status(
    session: Session,
    *,
    flow_id: str,
    task_name: str,
    status: str,
    error_message: str | None = None,
    started_at=None,
    finished_at=None,
):
    subtask = session.query(JobSubTask).filter(
        JobSubTask.flow_id == flow_id,
        JobSubTask.task_name == task_name,
    ).first()
    if subtask is None:
        return None
    subtask.status = status
    if error_message is not None:
        subtask.error_message = error_message
    if started_at is not None:
        subtask.started_at = started_at
    if finished_at is not None:
        subtask.finished_at = finished_at
    return subtask


def get_subtask_for_parent(
    session: Session,
    *,
    parent_type: str,
    parent_id: int,
    dag_task_id: str | None = None,
    subtask_db_id: int | None = None,
) -> JobSubTask | None:
    """Query by CSGHub dag_task_id (argo subtask id) or local subtask table id."""
    query = session.query(JobSubTask).filter(
        JobSubTask.parent_type == parent_type,
        JobSubTask.parent_id == parent_id,
    )
    if dag_task_id and str(dag_task_id).strip():
        return query.filter(JobSubTask.task_id == str(dag_task_id).strip()).first()
    if subtask_db_id is not None:
        return query.filter(JobSubTask.id == subtask_db_id).first()
    return None


def list_subtasks_for_parent(
    session: Session,
    *,
    parent_type: str,
    parent_id: int,
) -> list[dict]:
    items = (
        session.query(JobSubTask)
        .filter(
            JobSubTask.parent_type == parent_type,
            JobSubTask.parent_id == parent_id,
        )
        .order_by(JobSubTask.task_sequence.asc(), JobSubTask.id.asc())
        .all()
    )
    return [item.to_dict() for item in items]


def count_subtasks_for_parent(
    session: Session,
    *,
    parent_type: str,
    parent_id: int,
) -> int:
    return (
        session.query(JobSubTask)
        .filter(
            JobSubTask.parent_type == parent_type,
            JobSubTask.parent_id == parent_id,
        )
        .count()
    )


def sync_subtasks_status(
    session: Session,
    *,
    flow_id: str,
    subtask_items: list[dict],
) -> dict:
    subtasks = session.query(JobSubTask).filter(JobSubTask.flow_id == flow_id).all()
    by_task_id = {str(item.task_id): item for item in subtasks if item.task_id}
    by_task_name = {str(item.task_name): item for item in subtasks if item.task_name}

    updated = 0
    skipped = 0
    for item in subtask_items:
        if not isinstance(item, dict):
            skipped += 1
            continue

        task_id = item.get("task_id") or item.get("id") or item.get("subtask_id")
        task_name = item.get("task_name") or item.get("name") or item.get("subtask_name")
        subtask = None
        if task_id is not None:
            subtask = by_task_id.get(str(task_id))
        if subtask is None and task_name is not None:
            subtask = by_task_name.get(str(task_name))
        if subtask is None:
            skipped += 1
            continue

        status = item.get("status") or item.get("state") or item.get("phase")
        if status:
            subtask.status = str(status)
        error_message = item.get("error_message") or item.get("message") or item.get("error")
        if error_message:
            subtask.error_message = str(error_message)

        started_at = _parse_datetime(
            item.get("started_at") or item.get("start_time") or item.get("startedAt")
        )
        finished_at = _parse_datetime(
            item.get("finished_at") or item.get("finish_time") or item.get("finishedAt")
        )
        if started_at is not None:
            subtask.started_at = started_at
        if finished_at is not None:
            subtask.finished_at = finished_at
        updated += 1

    return {
        "flow_id": flow_id,
        "total": len(subtasks),
        "updated": updated,
        "skipped": skipped,
    }


def _parse_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except Exception:
            return None
    text = str(value).strip()
    if not text:
        return None

    for parser in (
        datetime.fromisoformat,
        lambda raw: datetime.strptime(raw, "%Y-%m-%d %H:%M:%S"),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d %H:%M:%S.%f"),
    ):
        try:
            return parser(text.replace("Z", "+00:00"))
        except Exception:
            continue
    return None


def _map_subtask_status_to_operator_status(status: str | None) -> str:
    key = str(status or "").strip().lower()
    if key in {"finished", "success", "succeeded", "completed", "done"}:
        return "success"
    if key in {"running", "processing", "executing", "in_progress"}:
        return "processing"
    if key in {"failed", "error", "timeout", "stopped", "cancelled", "canceled"}:
        return "error"
    return "waiting"


def _datetime_to_timestamp(dt) -> int | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return int(dt.timestamp())
    parsed = _parse_datetime(dt)
    if parsed is None:
        return None
    return int(parsed.timestamp())


def _extract_operator_index(subtask: JobSubTask, fallback: int = 0) -> int:
    payload = subtask.request_payload
    if not payload:
        return fallback
    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            idx = data.get("operator_index")
            if idx is not None:
                return int(idx)
    except Exception:
        pass
    return fallback


def _subtask_to_operator_status(
    subtask: JobSubTask,
    job_uid: str,
    operator_index: int,
) -> dict:
    return {
        "_id": f"{job_uid}-{subtask.task_name}-{operator_index}",
        "job_uid": job_uid,
        "operator_name": subtask.task_name,
        "operator_index": operator_index,
        "dag_task_id": subtask.task_id,
        "task_id": subtask.task_id,
        "status": _map_subtask_status_to_operator_status(subtask.status),
        "start_time": _datetime_to_timestamp(subtask.started_at),
        "end_time": _datetime_to_timestamp(subtask.finished_at),
    }


def _list_operator_subtasks(
    session: Session,
    *,
    parent_type: str,
    parent_id: int,
    flow_id: str | None = None,
) -> list[JobSubTask]:
    query = session.query(JobSubTask).filter(
        JobSubTask.task_type.in_(OPERATOR_SUBTASK_TASK_TYPES),
        JobSubTask.task_name.notin_(NON_OPERATOR_SUBTASK_NAMES),
    )

    if flow_id:
        subtasks = (
            query.filter(JobSubTask.flow_id == flow_id)
            .order_by(JobSubTask.task_sequence.asc(), JobSubTask.id.asc())
            .all()
        )
        if subtasks:
            return subtasks

    return (
        query.filter(
            JobSubTask.parent_type == parent_type,
            JobSubTask.parent_id == parent_id,
        )
        .order_by(JobSubTask.task_sequence.asc(), JobSubTask.id.asc())
        .all()
    )


def get_pipline_job_operators_status_from_subtasks(
    session: Session,
    *,
    parent_type: str,
    parent_id: int,
    job_uid: str,
    flow_id: str | None = None,
    operators: list[OperatorIdentifierItem] | None = None,
) -> list[dict]:
    """Read pipeline operator status from job_subtasks (replaces local operator_status file)."""
    subtasks = _list_operator_subtasks(
        session,
        parent_type=parent_type,
        parent_id=parent_id,
        flow_id=flow_id,
    )
    status_list = []
    for fallback_index, subtask in enumerate(subtasks):
        operator_index = _extract_operator_index(subtask, fallback=fallback_index)
        status_list.append(
            _subtask_to_operator_status(subtask, job_uid, operator_index)
        )

    if not operators:
        status_list.sort(key=lambda item: item.get("operator_index", 0))
        return status_list

    operator_names = {op.name for op in operators}
    operator_indices = {op.index for op in operators}
    filtered = [
        item
        for item in status_list
        if item.get("operator_name") in operator_names
        and item.get("operator_index") in operator_indices
    ]
    filtered.sort(key=lambda item: item.get("operator_index", 0))
    return filtered


def get_pipline_job_total_operators_status_from_subtasks(
    session: Session,
    *,
    parent_type: str,
    parent_id: int,
    job_uid: str,
    flow_id: str | None = None,
) -> list[dict]:
    return get_pipline_job_operators_status_from_subtasks(
        session,
        parent_type=parent_type,
        parent_id=parent_id,
        job_uid=job_uid,
        flow_id=flow_id,
        operators=None,
    )
