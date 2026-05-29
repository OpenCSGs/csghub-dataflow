import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from data_server.log_tools.tools import get_log_List, get_pipline_job_log_List
from data_server.database.session import get_sync_session
from data_server.datasource.DatasourceManager import (
    get_collection_task_by_uid,
    read_task_log,
)
from data_server.formatify.FormatifyManager import get_formatify_task_by_uid
from data_server.job.JobsManager import get_job_by_uid, retreive_log
from data_server.job.SubTaskManager import get_subtask_for_parent
from data_server.schemas.responses import response_fail, response_success
from data_server.utils.csghub_task_logs import fetch_csghub_logs_payload
from loguru import logger

router = APIRouter()


def _logs_text_to_task_log_list(logs_text: str, page: int, page_size: int) -> dict:
    """Convert CSGHub/local plain-text log to legacy task_log/list pagination."""
    lines = [line for line in str(logs_text or "").split("\n") if line.strip()]
    now = int(time.time())
    entries = [
        {
            "_id": str(index),
            "level": "INFO",
            "content": line,
            "create_at": now,
        }
        for index, line in enumerate(lines)
    ]
    total_count = len(entries)
    skip_count = (page - 1) * page_size
    page_entries = entries[skip_count: skip_count + page_size]
    return {
        "data": page_entries,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 0,
    }


def _fetch_datasource_logs_text(
    db: Session,
    *,
    task_uid: str,
    dag_task_id: str | None,
    stream: bool,
    user_token: str | None,
    authorization: str | None,
) -> str:
    collection_task = get_collection_task_by_uid(db, task_uid)
    if not collection_task:
        raise ValueError(f"任务不存在: {task_uid}")

    logger.info(
        "task_log datasource fetch | task_uid={uid} | task_id={tid} | "
        "has_csghub_job_id={has_csghub} | csghub_job_id={cjid} | dag_task_id={dag}",
        uid=task_uid,
        tid=collection_task.id,
        has_csghub=bool(collection_task.csghub_job_id),
        cjid=collection_task.csghub_job_id or "(empty)",
        dag=dag_task_id or "(main)",
    )

    if collection_task.csghub_job_id:
        if dag_task_id:
            subtask = get_subtask_for_parent(
                db,
                parent_type="datasource",
                parent_id=collection_task.id,
                dag_task_id=dag_task_id,
            )
            if subtask is None:
                raise ValueError(f"子任务不存在: {dag_task_id}")
        payload = fetch_csghub_logs_payload(
            namespace_uuid=collection_task.namespace_uuid,
            csghub_job_id=collection_task.csghub_job_id,
            flow_id=collection_task.flow_id,
            csghub_response_payload=collection_task.csghub_response_payload,
            dag_task_id=dag_task_id,
            stream=stream,
            user_token=user_token,
            authorization=authorization,
        )
        logs = payload.get("logs") or ""
        logger.info(
            "task_log datasource csghub result | task_uid={uid} | scope={scope} | logs_len={logs_len}",
            uid=task_uid,
            scope=payload.get("scope"),
            logs_len=len(logs),
        )
        return logs

    if dag_task_id:
        raise ValueError("任务未提交到 CSGHub，无法按子任务查询远端日志")

    result, content = read_task_log(collection_task)
    if not result:
        raise RuntimeError(f"读取日志失败:{content}")
    logger.info(
        "task_log datasource local result | task_uid={uid} | logs_len={logs_len}",
        uid=task_uid,
        logs_len=len(content or ""),
    )
    return content or ""


def _fetch_formatify_logs_text(
    db: Session,
    *,
    task_uid: str,
    dag_task_id: str | None,
    stream: bool,
    user_token: str | None,
    authorization: str | None,
) -> str:
    formatify_task = get_formatify_task_by_uid(db, task_uid)
    if not formatify_task:
        raise ValueError(f"任务不存在: {task_uid}")

    logger.info(
        "task_log formatify fetch | task_uid={uid} | task_id={tid} | "
        "has_csghub_job_id={has_csghub} | csghub_job_id={cjid} | dag_task_id={dag}",
        uid=task_uid,
        tid=formatify_task.id,
        has_csghub=bool(formatify_task.csghub_job_id),
        cjid=formatify_task.csghub_job_id or "(empty)",
        dag=dag_task_id or "(main)",
    )

    if formatify_task.csghub_job_id:
        if dag_task_id:
            subtask = get_subtask_for_parent(
                db,
                parent_type="formatify",
                parent_id=formatify_task.id,
                dag_task_id=dag_task_id,
            )
            if subtask is None:
                raise ValueError(f"子任务不存在: {dag_task_id}")
        payload = fetch_csghub_logs_payload(
            namespace_uuid=formatify_task.namespace_uuid,
            csghub_job_id=formatify_task.csghub_job_id,
            flow_id=formatify_task.flow_id,
            csghub_response_payload=formatify_task.csghub_response_payload,
            dag_task_id=dag_task_id,
            stream=stream,
            user_token=user_token,
            authorization=authorization,
        )
        logs = payload.get("logs") or ""
        logger.info(
            "task_log formatify csghub result | task_uid={uid} | scope={scope} | logs_len={logs_len}",
            uid=task_uid,
            scope=payload.get("scope"),
            logs_len=len(logs),
        )
        return logs

    if dag_task_id:
        raise ValueError("任务未提交到 CSGHub，无法按子任务查询远端日志")

    log_list = get_log_List(
        task_uid=task_uid,
        page=1,
        page_size=1000000,
        type="formatity",
    )
    entries = (log_list or {}).get("data") or []
    lines = [
        f"{entry.get('content', '')}"
        for entry in entries
        if entry.get("content")
    ]
    return "\n".join(lines)


def _fetch_job_logs_text(
    db: Session,
    *,
    task_uid: str,
    dag_task_id: str | None,
    stream: bool,
    user_token: str | None,
    authorization: str | None,
) -> str:
    job = get_job_by_uid(db, task_uid)
    if not job:
        raise ValueError(f"任务不存在: {task_uid}")

    parent_type = job.job_source or "pipeline"
    if parent_type not in ("pipeline", "tool"):
        parent_type = "pipeline"

    logger.info(
        "task_log job fetch | task_uid={uid} | job_id={jid} | job_source={src} | "
        "has_csghub_job_id={has_csghub} | csghub_job_id={cjid} | dag_task_id={dag}",
        uid=task_uid,
        jid=job.job_id,
        src=parent_type,
        has_csghub=bool(job.csghub_job_id),
        cjid=job.csghub_job_id or "(empty)",
        dag=dag_task_id or "(main)",
    )

    if job.csghub_job_id and parent_type in ("pipeline", "tool", "datasource"):
        if dag_task_id:
            subtask = get_subtask_for_parent(
                db,
                parent_type=parent_type,
                parent_id=job.job_id,
                dag_task_id=dag_task_id,
            )
            if subtask is None:
                raise ValueError(f"子任务不存在: {dag_task_id}")
        payload = fetch_csghub_logs_payload(
            namespace_uuid=job.namespace_uuid,
            csghub_job_id=job.csghub_job_id,
            flow_id=job.flow_id,
            csghub_response_payload=job.csghub_response_payload,
            dag_task_id=dag_task_id,
            stream=stream,
            user_token=user_token,
            authorization=authorization,
        )
        logs = payload.get("logs") or ""
        logger.info(
            "task_log job csghub result | task_uid={uid} | scope={scope} | logs_len={logs_len}",
            uid=task_uid,
            scope=payload.get("scope"),
            logs_len=len(logs),
        )
        return logs

    if dag_task_id:
        raise ValueError("任务未提交到 CSGHub，无法按子任务查询远端日志")

    if parent_type == "pipeline":
        log_list = get_pipline_job_log_List(
            task_uid=task_uid,
            page=1,
            page_size=1000000,
        )
    else:
        log_list = get_log_List(
            task_uid=task_uid,
            page=1,
            page_size=1000000,
            type="tool",
        )
    entries = (log_list or {}).get("data") or []
    if entries:
        lines = [entry.get("content", "") for entry in entries if entry.get("content")]
        if lines:
            return "\n".join(lines)

    log = retreive_log(job_id=job.job_id, user_id=job.owner_id, session=db, isadmin=True)
    if isinstance(log, dict):
        return log.get("session_log") or ""
    return str(log or "")


@router.get("/list", response_model=dict)
async def get_list(
    request: Request,
    task_uid: str,
    type: str,
    page: int = 1,
    page_size: int = 10,
    level: str = None,
    dag_task_id: str | None = None,
    subtask_id: str | None = None,
    stream: bool = True,
    db: Session = Depends(get_sync_session),
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    resolved_dag_task_id = (
        str(dag_task_id or subtask_id or "").strip() or None
    )
    logger.info(
        "task_log API hit | task_uid={uid} | type={typ} | page={page} | "
        "dag_task_id={dag} | subtask_id={sub} | stream={stream} | raw_query={raw}",
        uid=task_uid,
        typ=type,
        page=page,
        dag=dag_task_id or "(none)",
        sub=subtask_id or "(none)",
        stream=stream,
        raw=dict(request.query_params),
    )

    if type == "datasource":
        try:
            logs_text = _fetch_datasource_logs_text(
                db,
                task_uid=task_uid,
                dag_task_id=resolved_dag_task_id,
                stream=stream,
                user_token=user_token,
                authorization=authorization,
            )
            return response_success(
                data=_logs_text_to_task_log_list(logs_text, page, page_size)
            )
        except ValueError as exc:
            return response_fail(msg=str(exc))
        except RuntimeError as exc:
            return response_fail(msg=str(exc))
        except Exception as exc:
            logger.error(f"task_log datasource failed: {exc}")
            return response_fail(msg="读取日志失败")

    if type in ("formatity", "formatify"):
        try:
            logs_text = _fetch_formatify_logs_text(
                db,
                task_uid=task_uid,
                dag_task_id=resolved_dag_task_id,
                stream=stream,
                user_token=user_token,
                authorization=authorization,
            )
            return response_success(
                data=_logs_text_to_task_log_list(logs_text, page, page_size)
            )
        except ValueError as exc:
            return response_fail(msg=str(exc))
        except RuntimeError as exc:
            return response_fail(msg=str(exc))
        except Exception as exc:
            logger.error(f"task_log formatify failed: {exc}")
            return response_fail(msg="读取日志失败")

    if type in ("job", "pipeline", "tool"):
        try:
            logs_text = _fetch_job_logs_text(
                db,
                task_uid=task_uid,
                dag_task_id=resolved_dag_task_id,
                stream=stream,
                user_token=user_token,
                authorization=authorization,
            )
            return response_success(
                data=_logs_text_to_task_log_list(logs_text, page, page_size)
            )
        except ValueError as exc:
            return response_fail(msg=str(exc))
        except RuntimeError as exc:
            return response_fail(msg=str(exc))
        except Exception as exc:
            logger.error(f"task_log job failed: {exc}")
            return response_fail(msg="读取日志失败")

    log_list = get_log_List(
        task_uid=task_uid,
        page=page,
        page_size=page_size,
        level=level,
        type=type,
    )
    return response_success(data=log_list)
