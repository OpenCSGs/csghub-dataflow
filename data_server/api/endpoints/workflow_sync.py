import os

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from loguru import logger
from sqlalchemy.orm import Session

from data_server.database.session import get_sync_session
from data_server.schemas.responses import (
    response_fail,
    response_fail400,
    response_fail401,
    response_success,
)
from data_server.utils.workflow_sync_store import WORKFLOW_EVENTS, apply_workflow_sync


router = APIRouter()


class SubtaskSyncPayload(BaseModel):
    task_id: str | None = None
    task_name: str | None = None
    task_type: str | None = None
    status: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None

    model_config = ConfigDict(extra="allow")


class MainTaskSyncPayload(BaseModel):
    status: str | None = None
    csghub_status: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

    model_config = ConfigDict(extra="allow")


class UploadSyncPayload(BaseModel):
    repo_id: str | None = None
    branch: str | None = None

    model_config = ConfigDict(extra="allow")


class WorkflowSyncRequest(BaseModel):
    flow_id: str
    job_id: int | None = None
    event: str = Field(
        ...,
        description="step_started | step_finished | step_failed | workflow_finished",
    )
    finalize: bool = False
    message: str | None = None
    main: MainTaskSyncPayload | None = None
    current_subtask: SubtaskSyncPayload | None = None
    subtasks: list[SubtaskSyncPayload] | None = None
    upload: UploadSyncPayload | None = None


@router.post("/sync", response_model=dict)
async def sync_workflow_from_pod(
    payload: WorkflowSyncRequest,
    internal_token: str | None = Header(default=None, alias="X-Dataflow-Internal-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_session),
):
    expected_token = os.getenv("CSGHUB_DATAFLOW_CALLBACK_TOKEN", "").strip()
    has_jwt = bool(authorization and str(authorization).strip())
    if expected_token and internal_token != expected_token and not has_jwt:
        return response_fail401(msg="Unauthorized")

    if payload.event not in WORKFLOW_EVENTS:
        return response_fail400(
            msg=f"不支持的 event: {payload.event}，允许: {', '.join(sorted(WORKFLOW_EVENTS))}"
        )

    try:
        result = apply_workflow_sync(
            db,
            flow_id=payload.flow_id,
            event=payload.event,
            job_id=payload.job_id,
            finalize=payload.finalize,
            main=payload.main.model_dump(exclude_none=True) if payload.main else None,
            current_subtask=(
                payload.current_subtask.model_dump(exclude_none=True)
                if payload.current_subtask
                else None
            ),
            subtasks=(
                [s.model_dump(exclude_none=True) for s in payload.subtasks]
                if payload.subtasks
                else None
            ),
            upload=payload.upload.model_dump(exclude_none=True) if payload.upload else None,
            message=payload.message,
        )
        return response_success(data=result)
    except ValueError as exc:
        return response_fail400(msg=str(exc))
    except Exception as exc:
        logger.exception("sync_workflow_from_pod failed: {}", exc)
        return response_fail(msg=f"工作流同步失败: {exc}")
    finally:
        db.close()
