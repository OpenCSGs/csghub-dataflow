from datetime import datetime, timezone

from loguru import logger

from data_server.pod.common_tasks import (
    _mark_collection_task_failed,
    run_data_harvesting,
    run_format_conversion,
    run_operator_execute,
    run_pull_data,
    run_tool_execute,
    run_upload_data,
)
from data_server.pod.job_progress import extract_job_progress_from_task_result
from data_server.pod.pod_logger import log_task_error
from data_server.pod.workflow_sync_client import (
    is_workflow_finalize_step,
    push_workflow_sync,
)

# Human-readable English names per stage, used in the error report (issue #213).
_STAGE_LABELS = {
    "pull_data": "pull data (download source dataset)",
    "data_harvesting": "data harvesting (collect from external datasource)",
    "tool_execute": "tool execution",
    "operator_execute": "operator execution",
    "format_conversion": "format conversion",
    "upload_data": "upload data (push result dataset)",
}


def _build_task_error_report(task_type: str, task_params: dict, exc: BaseException) -> str:
    """Build a concise English error reason for a failed Argo stage (issue #213).

    Only the root-cause reason is reported (exception type + message + failing
    stage). The full stack trace is intentionally NOT included here: it is noise
    in the task log; the concise reason is what users need to act on.
    """
    stage_name = (
        task_params.get("current_task_name")
        or task_params.get("task_stage")
        or task_type
    )
    stage_label = _STAGE_LABELS.get(task_type, task_type)
    exc_type = type(exc).__name__
    exc_msg = str(exc).strip() or "(no message)"

    context = f"stage={stage_name} flow_id={task_params.get('flow_id')}"
    job_id = task_params.get("job_id")
    if job_id is not None:
        context += f" job_id={job_id}"

    return (
        f"[{task_type}] Task failed during {stage_label}. "
        f"Reason: {exc_type}: {exc_msg} ({context})"
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _resolve_task_type(task_type: str, task_params: dict) -> str:
    logical = task_params.get("current_task_type") or task_params.get("task_stage") or task_type
    aliases = {
        "datasource": "data_harvesting",
        "upload": "upload_data",
        "pull": "pull_data",
        "formatify": "format_conversion",
        "tool": "tool_execute",
        "pipeline": "operator_execute",
    }
    normalized = str(logical).strip()
    return aliases.get(normalized, normalized)


def _extract_task_progress(result) -> dict[str, int]:
    if not isinstance(result, dict):
        return {}
    progress: dict[str, int] = {}
    for key in ("records_count", "total_count", "success_count", "failure_count"):
        value = result.get(key)
        if value is not None:
            try:
                progress[key] = int(value)
            except (TypeError, ValueError):
                continue
    progress.update(extract_job_progress_from_task_result(result))
    return progress


def _sync_step_success(task_type: str, task_params: dict, started_at: str, result):
    """
    Business succeeded; workflow/sync write failure is logged only, does not fail Pod.
    Local status can be compensated via detail page sync_status from CSGHub.
    """
    finished_at = _utc_now_iso()
    finalize = is_workflow_finalize_step(task_type, task_params)
    upload = None
    if finalize and isinstance(result, dict):
        repo = result.get("upload_repo_id") or result.get("repo_id")
        branch = result.get("upload_branch") or result.get("branch")
        if repo and branch:
            upload = {"repo_id": str(repo), "branch": str(branch)}
            logger.info(
                "workflow finalize | flow_id={} | task_type={} | syncing actual upload branch "
                "back to task record: repo_id={} branch={}",
                task_params.get("flow_id"),
                task_type,
                repo,
                branch,
            )

    progress = _extract_task_progress(result)

    sync_kwargs = dict(
        task_params=task_params,
        started_at=started_at,
        finished_at=finished_at,
        progress=progress or None,
        fail_on_error=False,
    )
    try:
        if finalize:
            push_workflow_sync(
                event="workflow_finished",
                finalize=True,
                main_status="Succeeded",
                upload=upload,
                **sync_kwargs,
            )
        else:
            push_workflow_sync(
                event="step_finished",
                finalize=False,
                **sync_kwargs,
            )
    except Exception as exc:
        flow_id = task_params.get("flow_id")
        logger.warning(
            "workflow step success sync failed (pod still succeeds) flow_id={}: {}; "
            "compensate via detail sync_status if needed",
            flow_id,
            exc,
        )


def _sync_step_failed(task_type: str, task_params: dict, started_at: str, error_message: str):
    finished_at = _utc_now_iso()
    finalize = is_workflow_finalize_step(task_type, task_params)
    try:
        sync_result = push_workflow_sync(
            task_params=task_params,
            event="step_failed" if not finalize else "workflow_finished",
            finalize=finalize,
            started_at=started_at,
            finished_at=finished_at,
            main_status="Failed",
            message=error_message,
            fail_on_error=False,
        )
        if sync_result is None:
            logger.error(
                "workflow failure sync returned None | flow_id={} | task_type={} | "
                "operator_name={} | current_task_name={} | hint=check authorization/internal token",
                task_params.get("flow_id"),
                task_type,
                task_params.get("operator_name"),
                task_params.get("current_task_name"),
            )
        elif (sync_result.get("subtask") or {}).get("skipped"):
            logger.error(
                "workflow failure sync: subtask not matched | flow_id={} | payload={}",
                task_params.get("flow_id"),
                sync_result.get("subtask"),
            )
    except Exception as exc:
        logger.warning("workflow failure sync failed: {}", exc)


def run_tool_task(task_params: dict):
    logger.info("Running tool_execute task in pod")
    return run_tool_execute(task_params)


def run_pipeline_task(task_params: dict):
    logger.info("Running operator_execute task in pod")
    return run_operator_execute(task_params)


def run_datasource_task(task_params: dict):
    logger.info("Running data_harvesting task in pod")
    return run_data_harvesting(task_params)


def run_formatify_task(task_params: dict):
    logger.info("Running format_conversion task in pod")
    return run_format_conversion(task_params)


def run_task(task_type: str, task_params: dict):
    task_type = _resolve_task_type(task_type, task_params)
    started_at = _utc_now_iso()
    # step_started sync is handled in run_dataflow_task.py before heavy imports
    try:
        if task_type == "pull_data":
            result = run_pull_data(task_params)
        elif task_type == "upload_data":
            result = run_upload_data(task_params)
        elif task_type == "tool_execute":
            result = run_tool_task(task_params)
        elif task_type == "operator_execute":
            result = run_pipeline_task(task_params)
        elif task_type == "data_harvesting":
            result = run_datasource_task(task_params)
        elif task_type == "format_conversion":
            result = run_formatify_task(task_params)
        elif task_type == "tool":
            result = run_tool_task(task_params)
        elif task_type == "pipeline":
            result = run_pipeline_task(task_params)
        elif task_type == "datasource":
            result = run_datasource_task(task_params)
        elif task_type == "formatify":
            result = run_formatify_task(task_params)
        else:
            raise ValueError(f"Unsupported task_type: {task_type}")
        _sync_step_success(task_type, task_params, started_at, result)
        return result
    except Exception as exc:
        # Surface a concise English root-cause reason (issue #213). The stack trace
        # is noise in the task log, so it is emitted only at DEBUG level; the task
        # log / task detail get just the reason.
        error_report = _build_task_error_report(task_type, task_params, exc)
        logger.error(error_report)
        logger.opt(exception=exc).debug("Full traceback for the failure above")
        is_collection = task_params.get("collection_task_id") is not None and task_type in {
            "data_harvesting",
            "upload_data",
            "datasource",
        }
        if is_collection:
            # Writes the reason to the collection task log (mark-failed hook).
            _mark_collection_task_failed(task_params, error_report)
        else:
            log_task_error(task_params.get("task_uid"), error_report)
        _sync_step_failed(task_type, task_params, started_at, error_report)
        raise
