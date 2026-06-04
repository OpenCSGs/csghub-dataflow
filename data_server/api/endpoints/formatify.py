from fastapi import FastAPI, APIRouter, HTTPException, status, Header, Depends, Body, Query
from oauthlib.uri_validate import query
from sqlalchemy.orm import Session
from typing import Annotated, Union, Optional
from loguru import logger
from data_server.database.session import get_sync_session
from data_server.schemas.responses import response_success, response_fail,response_fail400
from data_server.formatify.FormatifyModels import DataFormatTypeEnum, DataFormatTaskStatusEnum, DataFormatTask
from data_server.formatify.schemas import DataFormatTaskRequest
from data_server.formatify.FormatifyManager import (
    create_formatify_task,
    search_formatify_task,
    update_formatify_task,
    delete_formatify_task,
    get_formatify_task,
    get_formatify_task_for_user,
    stop_formatify_task,
    execute_formatify_task,
    execute_new_formatify_task,
    enrich_formatify_task_dict,
)
from data_server.utils.task_access import (
    can_delete_task,
    normalize_user_id,
    resolve_organization_admin_uuids_for_delete,
    resolve_organization_namespace_uuids_for_list,
)
from data_server.datasource.DatasourceManager import apply_cluster_resource_fields
from pycsghub.snapshot_download import snapshot_download
from data_server.log_tools.tools import get_progress_from_formatify_logs
from data_server.utils.csghub_status_sync import (
    should_query_csghub_status,
    sync_csghub_main_task_status_by_query,
)
import os
from sqlalchemy import func
router = APIRouter()


@router.get("/get_mineru_api_url", response_model=dict)
async def get_mineru_api_url():
    """
    Get currently configured MinerU engine parameters.
    Returns:
        Dict: response with current MinerU engine parameters
            - mineru_api_url: MinerU API server URL
            - mineru_backend: MinerU backend type
            - sources: config source dict
                - mineru_api_url_source: source of mineru_api_url ("environment" | "default")
                - mineru_backend_source: source of mineru_backend ("environment" | "default")
    """
    try:
        # Get mineru_api_url from environment variable, use default value if not set
        mineru_api_url = os.getenv("MINERU_API_URL", "http://111.4.242.20:30000")
        mineru_api_url_source = "environment" if os.getenv("MINERU_API_URL") else "default"
        
        # Get mineru_backend from environment variable, use default value if not set
        mineru_backend = os.getenv("MINERU_BACKEND", "http-client")
        mineru_backend_source = "environment" if os.getenv("MINERU_BACKEND") else "default"
        
        return response_success(data={
            "mineru_api_url": mineru_api_url,
            "mineru_backend": mineru_backend,
            "sources": {
                "mineru_api_url_source": mineru_api_url_source,
                "mineru_backend_source": mineru_backend_source
            }
        })
    except Exception as e:
        logger.error(f"Failed to get mineru_api_url: {str(e)}")
        return response_fail(msg="获取 MinerU 引擎参数失败")


@router.get("/formatify/get_format_type_list", response_model=dict)
async def get_format_type_list():
    """
    Get list of data format types
    Returns:
        Dict: Dictionary containing two keys:
            - "data_format_1": First data format type list
            - "data_format_2": Second data format type list
    """
    data_format_types = {
        "data_format_1": {
            "from_format_types": [
                {"value": DataFormatTypeEnum.Excel.value, "label": DataFormatTypeEnum.Excel.name},
            ],
            "to_format_types": [
                {"value": DataFormatTypeEnum.Json.value, "label": DataFormatTypeEnum.Json.name},
                {"value": DataFormatTypeEnum.Csv.value, "label": DataFormatTypeEnum.Csv.name},
                {"value": DataFormatTypeEnum.Parquet.value, "label": DataFormatTypeEnum.Parquet.name},
            ]
        },
        "data_format_2": {
            "from_format_types": [
                {"value": DataFormatTypeEnum.Word.value, "label": DataFormatTypeEnum.Word.name},
                {"value": DataFormatTypeEnum.PPT.value, "label": DataFormatTypeEnum.PPT.name},
                {"value": DataFormatTypeEnum.PDF.value, "label": DataFormatTypeEnum.PDF.name},
                {"value": DataFormatTypeEnum.Txt.value, "label": DataFormatTypeEnum.Txt.name},
                {"value": DataFormatTypeEnum.Html.value, "label": DataFormatTypeEnum.Html.name},
            ],
            "to_format_types": [
                {"value": DataFormatTypeEnum.Markdown.value, "label": DataFormatTypeEnum.Markdown.name},
            ]
        },
    }
    return response_success(data=data_format_types)


@router.get("/get_task_statistics", response_model=dict)
async def get_task_statistics(db: Session = Depends(get_sync_session)):
    status_counts = db.query(
        DataFormatTask.task_status,
        func.count(DataFormatTask.id).label('count')
    ).filter(DataFormatTask.is_active.is_(True)).group_by(DataFormatTask.task_status).all()
    statistics = {}
    for status, count in status_counts:
        status_name = DataFormatTaskStatusEnum(status).name
        statistics[status_name] = count
    for status_enum in DataFormatTaskStatusEnum:
        if status_enum.name not in statistics:
            statistics[status_enum.name] = 0
    return response_success(data=statistics)

@router.post("/formatify/create", response_model=dict)
async def create_formatify_task_api(dataFormatTask: DataFormatTaskRequest,
                                    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
                                    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
                                    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
                                    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
                                    owner_org_id: Annotated[str | None, Header(alias="Org-Id")] = None,
                                    owner_org_name: Annotated[str | None, Header(alias="Org-Name")] = None
                                    ):
    """
    Create a format conversion task
    Args:
        dataFormatTask (DataFormatTaskRequest): Format conversion task request object
        user_id (str): User ID
        user_name (str): User name
        user_token (str): User token
    Returns:
        Dict: Response containing the created format conversion task ID
    """
    try:
        logger.info(f"Create formatify task: {dataFormatTask}")
        db = get_sync_session()
        formatify_task_id = create_formatify_task(
            db, dataFormatTask, user_id, user_name, user_token,
            owner_org_id=owner_org_id, owner_org_name=owner_org_name,
        )
        return response_success(data=formatify_task_id)
    except Exception as e:
        logger.error(f"Failed to create formatify task: {str(e)}")
        return response_fail(msg="Failed to create format conversion task")


@router.get("/formatify/list", response_model=dict)
async def formatify_list(
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    namespace_uuid: Optional[str] = Query(None, description="管理员可选：按单个组织缩小范围"),
    name: str = None,
    page: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_sync_session),
):
    """
    Get list of format conversion tasks
    Args:
        user_id (Optional[str]): User ID passed via Header, defaults to None.
        isadmin (Optional[bool]): Whether user is admin, passed via Header, defaults to None.
        page (int): Page number, defaults to 1.
        pageSize (int): Number of items per page, defaults to 20.
        db (Session): Database session object injected via Depends.
    Returns:
        dict: Dictionary containing data source list and total record count.
    """
    try:
        query_dict = {}
        if name is not None:
            query_dict["name"] = name
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        formatify_tasks, total = search_formatify_task(
            user_id,
            db,
            isadmin,
            query_dict,
            page,
            pageSize,
            organization_namespace_uuids=org_uuids,
            namespace_uuid=namespace_uuid,
        )
        uid = normalize_user_id(user_id)
        return response_success(data={
            "list": [
                enrich_formatify_task_dict(task, user_id=uid, isadmin=isadmin)
                for task in formatify_tasks
            ],
            "total": total
        })
    except Exception as e:
        logger.error(f"Failed to formatify_list: {str(e)}")
        return response_fail(msg="Query failed")


@router.put("/formatify/edit/{formatify_id}", response_model=dict)
async def update_formatify(formatify_id: int,
                           dataFormatTaskRequest: DataFormatTaskRequest,
                           db: Session = Depends(get_sync_session)):
    """
    Update a format conversion task
    Args:
        formatify_id (int): ID of the format conversion task to update
        dataFormatTaskRequest (DataFormatTaskRequest): Updated task data
        db (Session): Database session from dependency injection
    Returns:
        dict: Response with updated data or failure message
    """
    try:
        data_source = update_formatify_task(db, formatify_id, dataFormatTaskRequest)
        if not data_source:
            return response_fail(msg="Update failed")
        return response_success(data=data_source)
    except Exception as e:
        logger.error(f"update_formatify: {str(e)}")
        return response_fail(msg=f"Update failed: {str(e)}")


@router.delete("/formatify/delete/{formatify_id}", response_model=dict)
async def delete_formatify(
    formatify_id: int,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_sync_session),
):
    """Logically delete format conversion task; creator or admin only."""
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        task = get_formatify_task_for_user(
            db,
            formatify_id,
            user_id,
            isadmin,
            organization_namespace_uuids=org_uuids,
        )
        if not task:
            return response_fail(msg="任务不存在或无权访问")
        if not can_delete_task(
            owner_id=task.owner_id,
            user_id=user_id,
            isadmin=isadmin,
            org_admin_uuids=resolve_organization_admin_uuids_for_delete(
                user_name=user_name,
                authorization=authorization,
                user_token=user_token,
                isadmin=isadmin,
            ),
            namespace_uuid=getattr(task, "namespace_uuid", None),
            namespace_type=getattr(task, "namespace_type", None),
        ):
            return response_fail(msg="仅任务创建者或管理员可删除")
        result = delete_formatify_task(db, formatify_id)
        if not result:
            return response_fail(msg="Deletion failed")
        return response_success(data=True)
    except ValueError as e:
        return response_fail(msg=str(e))
    except Exception as e:
        logger.error(f"delete_formatify: {str(e)}")
        return response_fail(msg=f"Deletion failed: {str(e)}")


def get_progress_from_formatify_logs_wrapper(task_uid: str) -> Optional[dict]:
    """
    Parse formatify task progress from PostgreSQL logs.
    Args:
        task_uid: unique task identifier
    Returns:
        dict: progress info, or None if parsing fails
    """
    try:
        return get_progress_from_formatify_logs(task_uid)
    except Exception as e:
        logger.warning(f"Failed to get progress from formatify logs: {str(e)}")
        return None


@router.get("/formatify/get/{formatify_id}", response_model=dict, description="格式转换任务详情；sync_status=true 时按条件向 CSGHub 拉取状态")
async def get_formatify(
    formatify_id: int,
    sync_status: bool = False,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_sync_session),
):
    """
    Get details of a specific format conversion task
    Args:
        formatify_id (int): ID of the format conversion task to retrieve
        db (Session): Database session from dependency injection
    Returns:
        dict: Response with task details and progress information
    """
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        result = get_formatify_task_for_user(
            db,
            formatify_id,
            user_id,
            isadmin,
            organization_namespace_uuids=org_uuids,
        )
        if not result:
            return response_fail(msg="Query failed")

        if sync_status and should_query_csghub_status(result, "formatify"):
            sync_csghub_main_task_status_by_query(
                    db,
                    flow_id=result.flow_id,
                    csghub_job_id=result.csghub_job_id,
                    user_token=user_token,
                    authorization=authorization,
                csghub_response_payload=result.csghub_response_payload,
            )
            db.refresh(result)
        
        user_id_int = int(user_id) if user_id not in (None, "") else 0
        task_dict = enrich_formatify_task_dict(
            result, user_id=user_id_int, isadmin=isadmin
        )
        
        # If task is running, completed or failed, try to parse progress information from log files
        # Even if task failed, log files may still contain progress information for display
        if result.task_status in [DataFormatTaskStatusEnum.EXECUTING.value, DataFormatTaskStatusEnum.COMPLETED.value, DataFormatTaskStatusEnum.ERROR.value]:
            if result.task_uid:
                progress_info = get_progress_from_formatify_logs_wrapper(task_uid=result.task_uid)
                if progress_info:
                    task_dict["progress"] = progress_info
        
        return response_success(data=task_dict)
    except Exception as e:
        logger.error(f"get_formatify: {str(e)}")
        return response_fail(msg=f"Query failed: {str(e)}")


@router.post("/formatify/execute/{formatify_id}", response_model=dict)
async def run_formatify_task(
    formatify_id: int,
    data: dict = Body(default={}),
    db: Session = Depends(get_sync_session),
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    """
    Format conversion list "Execute":
    - Waiting and not submitted to CSGHub: submit this record
    - Completed/failed/stopped: copy new task and submit; do not re-run old record
    """
    try:
        formatify_task = get_formatify_task(db, formatify_id)
        if not formatify_task:
            return response_fail(msg="任务不存在")
        if formatify_task.task_status == DataFormatTaskStatusEnum.EXECUTING.value:
            return response_fail(msg="该任务在执行中")

        apply_cluster_resource_fields(
            formatify_task,
            cluster_id=data.get("cluster_id"),
            cluster_name=data.get("cluster_name"),
            resource_id=data.get("resource_id"),
            resource_name=data.get("resource_name"),
            space_resource_id=data.get("space_resource_id"),
            storage_size=data.get("storage_size"),
        )
        db.commit()

        task_run_time = data.get("task_run_time")

        if formatify_task.task_status == DataFormatTaskStatusEnum.WAITING.value:
            if formatify_task.csghub_job_id:
                return response_fail(msg="任务已在等待执行，无需重复提交")
            result, msg = execute_formatify_task(
                db,
                formatify_task,
                user_name,
                user_token,
                task_run_time=task_run_time,
            )
        elif formatify_task.task_status in (
            DataFormatTaskStatusEnum.COMPLETED.value,
            DataFormatTaskStatusEnum.ERROR.value,
            DataFormatTaskStatusEnum.STOP.value,
        ):
            result, msg = execute_new_formatify_task(
                db,
                formatify_task,
                user_name,
                user_token,
                task_run_time=task_run_time,
            )
        else:
            return response_fail(msg="当前状态不支持执行")

        if result:
            return response_success(data="任务执行成功")
        return response_fail(msg="任务执行失败:" + (msg or ""))
    except Exception as e:
        logger.error(f"run_formatify_task failed: {e}")
        return response_fail(msg="任务执行失败")


# Stop task
@router.post("/formatify/stop/{formatify_id}", response_model=dict)
async def stop_formatify(
    formatify_id: int,
    db: Session = Depends(get_sync_session),
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    """
    Stop a running format conversion task
    Args:
        formatify_id (int): ID of the format conversion task to stop
        db (Session): Database session from dependency injection
    Returns:
        dict: Response indicating success or failure of stopping the task
    """
    try:
        formatify_task = get_formatify_task(db, formatify_id)
        if not formatify_task:
            return response_fail(msg="Task does not exist")
        if formatify_task.task_status not in (
            DataFormatTaskStatusEnum.EXECUTING.value,
            DataFormatTaskStatusEnum.WAITING.value,
        ):
            return response_fail(msg="Task execution has already ended")
        result, msg = stop_formatify_task(db, formatify_task, user_token=user_token)
        if result:
            return response_success(data=msg or "Task stopped successfully")
        return response_fail(msg=msg or "Task stop failed")
    except Exception as e:
        logger.error(f"stop_formatify: {str(e)}")
        return response_fail(msg=f"Stop failed: {str(e)}")
