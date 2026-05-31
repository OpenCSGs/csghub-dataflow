import os
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from loguru import logger

from data_server.database.session import get_sync_session
from data_server.schemas.responses import response_fail, response_fail400, response_fail401, response_success
from data_server.utils.csghub_status_sync import (
    sync_csghub_main_task_status,
    sync_csghub_main_task_status_by_query,
)


router = APIRouter()


class CSGHubStatusIdentityRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    flow_id: str | None = None
    csghub_job_id: str | None = Field(default=None, alias="job_id")

    @model_validator(mode="after")
    def validate_identity(self):
        if not self.flow_id and not self.csghub_job_id:
            raise ValueError("flow_id 和 job_id 不能同时为空")
        return self


class CSGHubStatusCallbackRequest(CSGHubStatusIdentityRequest):
    status: str
    message: str | None = None
    detail: Any | None = None


@router.post("/status/callback", response_model=dict)
async def sync_csghub_status_callback(
    payload: CSGHubStatusCallbackRequest,
    internal_token: str | None = Header(default=None, alias="X-Dataflow-Internal-Token"),
    db: Session = Depends(get_sync_session),
):
    expected_token = os.getenv("CSGHUB_DATAFLOW_CALLBACK_TOKEN", "").strip()
    if expected_token and internal_token != expected_token:
        return response_fail401(msg="Unauthorized")

    try:
        result = sync_csghub_main_task_status(
            db,
            flow_id=payload.flow_id,
            csghub_job_id=payload.csghub_job_id,
            status=payload.status,
            callback_payload=payload.model_dump(by_alias=True, exclude_none=True),
        )
        return response_success(data=result)
    except ValueError as exc:
        return response_fail400(msg=str(exc))
    except Exception as exc:
        logger.error(f"sync_csghub_status_callback failed: {exc}")
        return response_fail(msg=f"同步主任务状态失败: {exc}")
    finally:
        db.close()


@router.post("/status/query", response_model=dict)
async def query_csghub_status(
    payload: CSGHubStatusIdentityRequest,
    user_token: str | None = Header(default=None, alias="User-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_session),
):
    try:
        result = sync_csghub_main_task_status_by_query(
            db,
            flow_id=payload.flow_id,
            csghub_job_id=payload.csghub_job_id,
            user_token=user_token,
            authorization=authorization,
        )
        return response_success(data=result)
    except ValueError as exc:
        return response_fail400(msg=str(exc))
    except Exception as exc:
        logger.error(f"query_csghub_status failed: {exc}")
        return response_fail(msg=f"补偿查询主任务状态失败: {exc}")
    finally:
        db.close()
