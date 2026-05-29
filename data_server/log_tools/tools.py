"""
File logging tools module.
Keep the public function signatures compatible with the old mongo/pg helpers.
"""
import json
import os
import re
from enum import Enum
from typing import List, Optional

from data_server.utils.project_paths import get_project_root, get_timestamp
from data_server.logic.models import OperatorIdentifierItem


class LogLevelEnum(Enum):
    INFO = "info"
    ERROR = "error"
    WARNING = "warning"
    DEBUG = "debug"


class OperatorStatusEnum(Enum):
    Waiting = "waiting"
    Processing = "processing"
    SUCCESS = "success"
    ERROR = "error"


def _get_log_root() -> str:
    return os.path.join(str(get_project_root()), "runtime_logs")


def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _get_task_log_path(task_type: str, task_uid: str) -> str:
    safe_task_type = "formatify" if task_type == "formatity" else task_type
    return os.path.join(_get_log_root(), safe_task_type, f"{task_uid}.jsonl")


def _get_operator_status_path(job_uid: str) -> str:
    return os.path.join(_get_log_root(), "pipeline", f"{job_uid}.operator_status.json")


def _append_json_line(path: str, data: dict):
    _ensure_parent(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def _read_json_lines(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _read_operator_statuses(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_operator_statuses(path: str, data: list[dict]):
    _ensure_parent(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _safe_insert_log(
    task_uid: str,
    task_type: str,
    content: str,
    level: str,
    operator_name: str = None,
    operator_index: int = 0,
):
    """Secure log insertion to file, failure does not affect the main process."""
    if not task_uid:
        return
    try:
        log = {
            "_id": f"{task_uid}-{get_timestamp()}",
            "task_uid": task_uid,
            "task_type": task_type,
            "level": level,
            "operator_name": operator_name or "",
            "operator_index": operator_index or 0,
            "content": content,
            "create_at": get_timestamp(),
        }
        _append_json_line(_get_task_log_path(task_type, task_uid), log)
    except Exception as e:
        print(f"file insert {task_type} log failed, error: {e}")


def insert_pipline_job_run_task_log(
    job_uid: str,
    content: str,
    level: str,
    operator_name: str,
    operator_index: int = 0,
):
    _safe_insert_log(job_uid, "pipeline", content, level, operator_name, operator_index)


def insert_pipline_job_run_task_log_info(
    job_uid: str,
    content: str,
    operator_name: str = "",
    operator_index: int = 0,
):
    insert_pipline_job_run_task_log(
        job_uid, content, LogLevelEnum.INFO.value, operator_name, operator_index
    )


def insert_pipline_job_run_task_log_error(
    job_uid: str,
    content: str,
    operator_name: str = "",
    operator_index: int = 0,
):
    insert_pipline_job_run_task_log(
        job_uid, content, LogLevelEnum.ERROR.value, operator_name, operator_index
    )


def insert_pipline_job_run_task_log_warning(
    job_uid: str,
    content: str,
    operator_name: str = "",
    operator_index: int = 0,
):
    insert_pipline_job_run_task_log(
        job_uid, content, LogLevelEnum.WARNING.value, operator_name, operator_index
    )


def insert_pipline_job_run_task_log_debug(
    job_uid: str,
    content: str,
    operator_name: str = "",
    operator_index: int = 0,
):
    insert_pipline_job_run_task_log(
        job_uid, content, LogLevelEnum.DEBUG.value, operator_name, operator_index
    )


def insert_datasource_run_task_log(task_uid: str, content: str, level: str):
    _safe_insert_log(task_uid, "datasource", content, level)


def insert_datasource_run_task_log_info(task_uid: str, content: str):
    insert_datasource_run_task_log(task_uid, content, LogLevelEnum.INFO.value)


def insert_datasource_run_task_log_error(task_uid: str, content: str):
    insert_datasource_run_task_log(task_uid, content, LogLevelEnum.ERROR.value)


def insert_formatity_task_log(task_uid: str, content: str, level: str):
    _safe_insert_log(task_uid, "formatify", content, level)


def insert_formatity_task_log_info(task_uid: str, content: str):
    insert_formatity_task_log(task_uid, content, LogLevelEnum.INFO.value)


def insert_formatity_task_log_error(task_uid: str, content: str):
    insert_formatity_task_log(task_uid, content, LogLevelEnum.ERROR.value)


def get_log_List(
    task_uid: str,
    page: int = 1,
    page_size: int = 10,
    level: str = None,
    type: str = None,
):
    if type is None:
        raise ValueError("param type is not exist")
    if task_uid is None:
        raise ValueError("param task_uid is not exist")

    task_type = "formatify" if type == "formatity" else type
    logs = _read_json_lines(_get_task_log_path(task_type, task_uid))
    if level:
        logs = [log for log in logs if log.get("level") == level]
    logs.sort(key=lambda item: item.get("create_at", 0))

    total_count = len(logs)
    skip_count = (page - 1) * page_size
    logs = logs[skip_count: skip_count + page_size]
    result = [
        {
            "_id": str(log.get("_id", "")),
            "level": log.get("level"),
            "content": log.get("content"),
            "create_at": log.get("create_at"),
        }
        for log in logs
    ]
    return {
        "data": result,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 0,
    }


def get_pipline_job_log_List(
    task_uid: str,
    page: int = 1,
    page_size: int = 10,
    level: str = None,
    ops_name: str = None,
):
    if task_uid is None:
        raise ValueError("param task_uid is not exist")

    logs = _read_json_lines(_get_task_log_path("pipeline", task_uid))
    if level and len(level) > 0:
        logs = [log for log in logs if log.get("level") == level]
    if ops_name and len(ops_name) > 0:
        logs = [log for log in logs if log.get("operator_name") == ops_name]
    logs.sort(key=lambda item: item.get("create_at", 0))

    total_count = len(logs)
    skip_count = (page - 1) * page_size
    logs = logs[skip_count: skip_count + page_size]
    result = [
        {
            "_id": str(log.get("_id", "")),
            "level": log.get("level"),
            "content": log.get("content"),
            "create_at": log.get("create_at"),
            "operator_name": log.get("operator_name") or "",
            "operator_index": log.get("operator_index") or 0,
        }
        for log in logs
    ]
    return {
        "data": result,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 0,
    }


def set_pipline_job_operator_status(
    job_uid: str,
    status: OperatorStatusEnum,
    operator_name: str,
    operator_index: int = 0,
):
    if not job_uid or len(job_uid) == 0:
        return
    try:
        path = _get_operator_status_path(job_uid)
        statuses = _read_operator_statuses(path)
        existing = None
        for item in statuses:
            if (
                item.get("job_uid") == job_uid
                and item.get("operator_name") == operator_name
                and int(item.get("operator_index", 0)) == operator_index
            ):
                existing = item
                break

        if existing:
            existing["status"] = status.value
            existing["end_time"] = get_timestamp()
        else:
            statuses.append({
                "_id": f"{job_uid}-{operator_name}-{operator_index}",
                "job_uid": job_uid,
                "operator_name": operator_name,
                "operator_index": operator_index,
                "status": status.value,
                "start_time": get_timestamp(),
                "end_time": None,
            })
        _write_operator_statuses(path, statuses)
    except Exception as e:
        print(f"file set operator status failed, error: {e}")


def get_pipline_job_operators_status(
    job_uid: str, operators: List[OperatorIdentifierItem]
) -> List[dict]:
    """Deprecated: read operator status from job_subtasks; use SubTaskManager.get_pipline_job_operators_status_from_subtasks."""
    if not job_uid or len(job_uid) == 0 or not operators:
        return []
    return []


def get_pipline_job_total_operators_status(job_uid: str) -> List[dict]:
    """Deprecated: read operator status from job_subtasks; use SubTaskManager.get_pipline_job_total_operators_status_from_subtasks."""
    if not job_uid or len(job_uid) == 0:
        return []
    return []


def get_progress_from_formatify_logs(task_uid: str) -> Optional[dict]:
    if not task_uid:
        return None

    try:
        logs = [log for log in _read_json_lines(_get_task_log_path("formatify", task_uid)) if log.get("level") == "info"]
        logs.sort(key=lambda item: item.get("create_at", 0), reverse=True)
        logs = logs[:100]

        progress_patterns = [
            r"\(total:\s*(\d+),\s*success:\s*(\d+),\s*failure:\s*(\d+)\)",
            r"Total:\s*(\d+),\s*Success:\s*(\d+),\s*Failure:\s*(\d+)",
        ]

        for log in logs:
            content = log.get("content") or ""
            for pattern in progress_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    total = int(match.group(1))
                    success = int(match.group(2))
                    failure = int(match.group(3))
                    processed = success + failure
                    progress = round(processed / max(total, 1) * 100, 2) if total > 0 else 0
                    return {
                        "total": total,
                        "success": success,
                        "failure": failure,
                        "progress": progress,
                    }

        logs_for_total = list(reversed(logs[:50]))
        total_count = None
        for log in logs_for_total:
            content = log.get("content") or ""
            match = re.search(r"Found\s+(\d+)\s+files\s+to\s+convert", content, re.IGNORECASE)
            if match:
                total_count = int(match.group(1))
                break

        if total_count is not None:
            all_logs = _read_json_lines(_get_task_log_path("formatify", task_uid))
            success_count = sum(
                1 for log in all_logs
                if log.get("level") == "info"
                and log.get("content")
                and "convert file" in log["content"].lower()
                and "succeed" in log["content"].lower()
            )
            failure_count = sum(
                1 for log in all_logs
                if log.get("level") == "error"
                and log.get("content")
                and "convert file" in log["content"].lower()
                and "error" in log["content"].lower()
            )
            processed = success_count + failure_count
            progress = round(processed / max(total_count, 1) * 100, 2) if total_count > 0 else 0
            return {
                "total": total_count,
                "success": success_count,
                "failure": failure_count,
                "progress": progress,
            }
        return None
    except Exception as e:
        print(f"file get progress from formatify logs failed, error: {e}")
        return None
