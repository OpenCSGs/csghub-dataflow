import os

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from loguru import logger

from data_server.database.session import get_sync_session
from data_server.schemas.responses import response_fail, response_fail400, response_fail401, response_success
from data_server.utils.trace_sync_store import (
    bind_local_work_dir_for_entity,
    resolve_entity_by_flow_id,
    save_trace_files,
)


router = APIRouter()


class TraceFilePayload(BaseModel):
    """Matches Tracer output files: mapper-{op}.jsonl / filter-{op}.jsonl / duplicate-{op}.jsonl / count-{op}.txt"""

    name: str
    content: str | None = None
    content_base64: str | None = Field(default=None, alias="contentBase64")

    model_config = ConfigDict(populate_by_name=True)


class TraceSyncRequest(BaseModel):
    flow_id: str
    job_id: int | None = None
    operator_name: str = Field(..., description="当前 DAG 算子名，与 trace 文件名中 {op} 一致")
    operator_index: int | None = None
    sync_mode: str = Field(
        default="trace_only",
        description="trace_only：只写 trace/；init_config：仅当本地无 config.yaml 时写入",
    )
    files: list[TraceFilePayload] = Field(default_factory=list)
    config_yaml: str | None = Field(
        default=None,
        description="仅 sync_mode=init_config 时生效；禁止用单算子 yaml 覆盖完整 pipeline 配置",
    )

    @model_validator(mode="after")
    def validate_payload(self):
        if not self.files and self.sync_mode != "init_config":
            raise ValueError("files 不能为空（除非 sync_mode=init_config 且提供 config_yaml）")
        if self.sync_mode == "trace_only" and self.config_yaml:
            # Ignore mistaken single-operator config from Pod to avoid truncating frontend process list
            object.__setattr__(self, "config_yaml", None)
        return self


@router.post("/sync", response_model=dict)
async def sync_trace_from_pod(
    payload: TraceSyncRequest,
    internal_token: str | None = Header(default=None, alias="X-Dataflow-Internal-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_session),
):
    expected_token = os.getenv("CSGHUB_DATAFLOW_CALLBACK_TOKEN", "").strip()
    has_jwt = bool(authorization and str(authorization).strip())
    if expected_token and internal_token != expected_token and not has_jwt:
        return response_fail401(msg="Unauthorized")

    try:
        entity_type, entity = resolve_entity_by_flow_id(
            db, payload.flow_id, job_id=payload.job_id
        )
        result = save_trace_files(
            flow_id=payload.flow_id,
            files=[f.model_dump(by_alias=True, exclude_none=True) for f in payload.files],
            operator_name=payload.operator_name,
            sync_mode=payload.sync_mode,
            config_yaml=payload.config_yaml,
        )
        if entity_type == "job":
            bind_local_work_dir_for_entity(entity, payload.flow_id)
            db.commit()
        result["entity_type"] = entity_type
        result["operator_name"] = payload.operator_name
        result["operator_index"] = payload.operator_index
        return response_success(data=result)
    except ValueError as exc:
        return response_fail400(msg=str(exc))
    except Exception as exc:
        logger.exception("sync_trace_from_pod failed: {}", exc)
        return response_fail(msg=f"trace 回传失败: {exc}")
    finally:
        db.close()
