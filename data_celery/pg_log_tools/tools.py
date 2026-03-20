"""
PostgreSQL Logging Tools Module - Replacing the original MongoDB mongo_tools.tools
Maintain the signature and return format exactly the same as the original interface to ensure backward compatibility
"""
import re
from enum import Enum
from typing import List, Optional


from data_server.database.session import get_log_sync_session
from data_server.database.bean.task_log import TaskLog, OperatorStatus
from data_celery.utils import get_timestamp
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

def _safe_insert_log(
    task_uid: str,
    task_type: str,
    content: str,
    level: str,
    operator_name: str = None,
    operator_index: int = 0,
):
    """Secure log insertion, failure does not affect the main process"""
    if not task_uid:
        return
    session = None
    try:
        session = get_log_sync_session()
        log = TaskLog(
            task_uid=task_uid,
            task_type=task_type,
            level=level,
            operator_name=operator_name,
            operator_index=operator_index,
            content=content,
            create_at=get_timestamp(),
        )
        session.add(log)
        session.commit()
    except Exception as e:
        if session:
            session.rollback()
        print(f"pg insert {task_type} log failed, error: {e}")
    finally:
        if session:
            session.close()


# ==================== pipelineLogFunction ====================
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


# ==================== Datasource  ====================
def insert_datasource_run_task_log(task_uid: str, content: str, level: str):
    _safe_insert_log(task_uid, "datasource", content, level)


def insert_datasource_run_task_log_info(task_uid: str, content: str):
    insert_datasource_run_task_log(task_uid, content, LogLevelEnum.INFO.value)


def insert_datasource_run_task_log_error(task_uid: str, content: str):
    insert_datasource_run_task_log(task_uid, content, LogLevelEnum.ERROR.value)


# ==================== Formatify  ====================
def insert_formatity_task_log(task_uid: str, content: str, level: str):
    _safe_insert_log(task_uid, "formatify", content, level)


def insert_formatity_task_log_info(task_uid: str, content: str):
    insert_formatity_task_log(task_uid, content, LogLevelEnum.INFO.value)


def insert_formatity_task_log_error(task_uid: str, content: str):
    insert_formatity_task_log(task_uid, content, LogLevelEnum.ERROR.value)


# ==================== logReadingFunction ====================
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

    # Compatible with historical spelling: formatity -> formatify
    task_type = "formatify" if type == "formatity" else type

    session = get_log_sync_session()
    try:
        query = session.query(TaskLog).filter(
            TaskLog.task_uid == task_uid,
            TaskLog.task_type == task_type,
        )
        if level:
            query = query.filter(TaskLog.level == level)

        total_count = query.count()
        skip_count = (page - 1) * page_size
        logs = query.order_by(TaskLog.create_at).offset(skip_count).limit(page_size).all()

        result = [
            {
                "_id": str(log.id),
                "level": log.level,
                "content": log.content,
                "create_at": log.create_at,
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
    finally:
        session.close()


def get_pipline_job_log_List(
    task_uid: str,
    page: int = 1,
    page_size: int = 10,
    level: str = None,
    ops_name: str = None,
):
    """Pipeline log reading supports filtering by operator name"""
    if task_uid is None:
        raise ValueError("param task_uid is not exist")

    session = get_log_sync_session()
    try:
        query = session.query(TaskLog).filter(
            TaskLog.task_uid == task_uid,
            TaskLog.task_type == "pipeline",
        )
        if level and len(level) > 0:
            query = query.filter(TaskLog.level == level)
        if ops_name and len(ops_name) > 0:
            query = query.filter(TaskLog.operator_name == ops_name)

        total_count = query.count()
        skip_count = (page - 1) * page_size
        logs = (
            query.order_by(TaskLog.create_at)
            .offset(skip_count)
            .limit(page_size)
            .all()
        )

        result = [
            {
                "_id": str(log.id),
                "level": log.level,
                "content": log.content,
                "create_at": log.create_at,
                "operator_name": log.operator_name or "",
                "operator_index": log.operator_index or 0,
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
    finally:
        session.close()


# ==================== operatorStateFunction ====================
def set_pipline_job_operator_status(
    job_uid: str,
    status: OperatorStatusEnum,
    operator_name: str,
    operator_index: int = 0,
):
    """Set the state of the operator. If it exists, update; if not, insert"""
    if not job_uid or len(job_uid) == 0:
        return
    session = None
    try:
        session = get_log_sync_session()
        existing = (
            session.query(OperatorStatus)
            .filter(
                OperatorStatus.job_uid == job_uid,
                OperatorStatus.operator_name == operator_name,
                OperatorStatus.operator_index == operator_index,
            )
            .first()
        )

        if existing:
            existing.status = status.value
            existing.end_time = get_timestamp()
        else:
            new_status = OperatorStatus(
                job_uid=job_uid,
                operator_name=operator_name,
                operator_index=operator_index,
                status=status.value,
                start_time=get_timestamp(),
                end_time=None,
            )
            session.add(new_status)
        session.commit()
    except Exception as e:
        if session:
            session.rollback()
        print(f"pg set operator status failed, error: {e}")
    finally:
        if session:
            session.close()


def get_pipline_job_operators_status(
    job_uid: str, operators: List[OperatorIdentifierItem]
) -> List[dict]:
    """batchObtainTheOperatorStatus"""
    if not job_uid or len(job_uid) == 0 or not operators:
        return []

    session = get_log_sync_session()
    try:
        operator_names = [op.name for op in operators]
        operator_indices = [op.index for op in operators]

        results = (
            session.query(OperatorStatus)
            .filter(
                OperatorStatus.job_uid == job_uid,
                OperatorStatus.operator_name.in_(operator_names),
                OperatorStatus.operator_index.in_(operator_indices),
            )
            .all()
        )

        return [
            {
                "_id": str(r.id),
                "job_uid": r.job_uid,
                "operator_name": r.operator_name,
                "operator_index": r.operator_index,
                "status": r.status,
                "start_time": r.start_time,
                "end_time": r.end_time,
            }
            for r in results
        ]
    except Exception as e:
        print(f"pg query pipline job operators status failed, error: {e}")
        return []
    finally:
        session.close()


def get_pipline_job_total_operators_status(job_uid: str) -> List[dict]:
    """obtainTheStatesOfAllOperatorsOfTheJob"""
    if not job_uid or len(job_uid) == 0:
        return []

    session = get_log_sync_session()
    try:
        results = (
            session.query(OperatorStatus)
            .filter(OperatorStatus.job_uid == job_uid)
            .all()
        )

        return [
            {
                "_id": str(r.id),
                "job_uid": r.job_uid,
                "operator_name": r.operator_name,
                "operator_index": r.operator_index,
                "status": r.status,
                "start_time": r.start_time,
                "end_time": r.end_time,
            }
            for r in results
        ]
    except Exception as e:
        print(f"pg query pipline job operators status failed, error: {e}")
        return []
    finally:
        session.close()


# ====================Formatify progress Analysis (instead of get_formatity_collection + get_client) ====================
def get_progress_from_formatify_logs(task_uid: str) -> Optional[dict]:
    """
    Parse the formatify task progress information from PostgreSQL logs
Replace the MongoDB query logic in the original get_progress_from_mongodb_logs
    """
    if not task_uid:
        return None

    session = get_log_sync_session()
    try:
        # Search for logs containing progress information (in reverse chronological order, taking the most recent 100 entries)
        logs = (
            session.query(TaskLog)
            .filter(
                TaskLog.task_uid == task_uid,
                TaskLog.task_type == "formatify",
                TaskLog.level == "info",
            )
            .order_by(TaskLog.create_at.desc())
            .limit(100)
            .all()
        )

        progress_patterns = [
            r"\(total:\s*(\d+),\s*success:\s*(\d+),\s*failure:\s*(\d+)\)",
            r"Total:\s*(\d+),\s*Success:\s*(\d+),\s*Failure:\s*(\d+)",
        ]

        for log in logs:
            content = log.content or ""
            for pattern in progress_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    total = int(match.group(1))
                    success = int(match.group(2))
                    failure = int(match.group(3))
                    processed = success + failure
                    progress = (
                        round(processed / max(total, 1) * 100, 2) if total > 0 else 0
                    )
                    return {
                        "total": total,
                        "success": success,
                        "failure": failure,
                        "progress": progress,
                    }

        # Try to get the total from "Found X files to convert"
        logs_for_total = (
            session.query(TaskLog)
            .filter(
                TaskLog.task_uid == task_uid,
                TaskLog.task_type == "formatify",
                TaskLog.level == "info",
            )
            .order_by(TaskLog.create_at.asc())
            .limit(50)
            .all()
        )

        total_count = None
        for log in logs_for_total:
            content = log.content or ""
            match = re.search(r"Found\s+(\d+)\s+files\s+to\s+convert", content, re.IGNORECASE)
            if match:
                total_count = int(match.group(1))
                break

        if total_count is not None:
            # countTheNumberOfSuccessesAndFailures
            success_logs = (
                session.query(TaskLog)
                .filter(
                    TaskLog.task_uid == task_uid,
                    TaskLog.task_type == "formatify",
                    TaskLog.level == "info",
                )
                .all()
            )
            success_count = sum(
                1
                for log in success_logs
                if log.content and "convert file" in log.content.lower() and "succeed" in log.content.lower()
            )

            failure_logs = (
                session.query(TaskLog)
                .filter(
                    TaskLog.task_uid == task_uid,
                    TaskLog.task_type == "formatify",
                    TaskLog.level == "error",
                )
                .all()
            )
            failure_count = sum(
                1
                for log in failure_logs
                if log.content and "convert file" in log.content.lower() and "error" in log.content.lower()
            )

            processed = success_count + failure_count
            progress = (
                round(processed / max(total_count, 1) * 100, 2) if total_count > 0 else 0
            )
            return {
                "total": total_count,
                "success": success_count,
                "failure": failure_count,
                "progress": progress,
            }

        return None
    except Exception as e:
        print(f"pg get progress from formatify logs failed, error: {e}")
        return None
    finally:
        session.close()
