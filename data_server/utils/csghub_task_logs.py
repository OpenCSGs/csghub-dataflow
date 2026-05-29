"""Fetch DataFlow main/subtask logs from CSGHub."""

from __future__ import annotations

from typing import Any

from loguru import logger

from data_server.utils.csghub_client import fetch_csghub_job_logs, resolve_csghub_remote_job_id


def fetch_csghub_logs_payload(
    *,
    namespace_uuid: str | None,
    csghub_job_id: str | None,
    flow_id: str | None = None,
    csghub_response_payload: Any = None,
    dag_task_id: str | None = None,
    stream: bool = False,
    user_token: str | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Call CSGHub GET .../jobs/{job_id}/logs.
    Without dag_task_id: full main task log; with dag_task_id: corresponding subtask log.
    """
    namespace = str(namespace_uuid or "").strip()
    remote_job_id = resolve_csghub_remote_job_id(
        csghub_job_id,
        flow_id=flow_id,
        csghub_response_payload=csghub_response_payload,
    )
    logger.info(
        "CSGHub logs payload prepare | namespace={ns} | csghub_job_id={stored} | "
        "flow_id={fid} | remote_job_id={remote} | dag_task_id={dag} | stream={stream}",
        ns=namespace or "(empty)",
        stored=csghub_job_id or "(empty)",
        fid=flow_id or "(empty)",
        remote=remote_job_id or "(empty)",
        dag=dag_task_id or "(main)",
        stream=stream,
    )
    if not namespace or not remote_job_id:
        raise ValueError("任务尚未提交到 CSGHub，无法获取远端日志")

    logs = fetch_csghub_job_logs(
        namespace=namespace,
        csghub_job_id=remote_job_id,
        user_token=user_token,
        authorization=authorization,
        stream=stream,
        dag_task_id=dag_task_id,
    )
    logger.info(
        "CSGHub logs payload done | remote_job_id={remote} | dag_task_id={dag} | "
        "logs_len={logs_len}",
        remote=remote_job_id,
        dag=dag_task_id or "(main)",
        logs_len=len(logs or ""),
    )
    dag = str(dag_task_id).strip() if dag_task_id else None
    return {
        "logs": logs,
        "namespace_uuid": namespace,
        "csghub_job_id": remote_job_id,
        "flow_id": flow_id,
        "dag_task_id": dag,
        "scope": "subtask" if dag else "main",
        "stream": stream,
    }
