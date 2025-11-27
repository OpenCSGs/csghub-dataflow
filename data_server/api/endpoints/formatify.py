from fastapi import FastAPI, APIRouter, HTTPException, status, Header, Depends
from oauthlib.uri_validate import query
from sqlalchemy.orm import Session
from typing import Annotated, Union, Optional
from loguru import logger
from data_server.database.session import get_sync_session
from data_server.schemas.responses import response_success, response_fail,response_fail400
from data_server.formatify.FormatifyModels import DataFormatTypeEnum, DataFormatTaskStatusEnum, DataFormatTask
from data_server.formatify.schemas import DataFormatTaskRequest
from data_server.formatify.FormatifyManager import (create_formatify_task, search_formatify_task,
                                                    update_formatify_task, delete_formatify_task,
                                                    get_formatify_task, stop_formatify_task)
from pycsghub.snapshot_download import snapshot_download
from data_celery.mongo_tools.tools import get_formatity_collection, get_client
import os
import re
from sqlalchemy import func
router = APIRouter()


@router.get("/get_mineru_api_url", response_model=dict)
async def get_mineru_api_url():
    """
    获取当前配置的 MinerU API 地址
    Returns:
        Dict: 包含当前 MinerU API 地址的响应
            - mineru_api_url: MinerU API 服务器地址
            - source: 配置来源 ("environment" | "default")
    """
    try:
        # 从环境变量获取，如果没有则使用默认值
        mineru_api_url = os.getenv("MINERU_API_URL", "http://111.4.242.20:30000")
        source = "environment" if os.getenv("MINERU_API_URL") else "default"
        
        return response_success(data={
            "mineru_api_url": mineru_api_url,
            "source": source
        })
    except Exception as e:
        logger.error(f"Failed to get mineru_api_url: {str(e)}")
        return response_fail(msg="获取 MinerU API 地址失败")


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
    ).group_by(DataFormatTask.task_status).all()
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
                                    user_token: Annotated[str | None, Header(alias="User-Token")] = None
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
        formatify_task_id = create_formatify_task(db, dataFormatTask, user_id, user_name, user_token)
        return response_success(data=formatify_task_id)
    except Exception as e:
        logger.error(f"Failed to create formatify task: {str(e)}")
        return response_fail(msg="Failed to create format conversion task")


@router.get("/formatify/list", response_model=dict)
async def formatify_list(user_id: Annotated[str | None, Header(alias="User-Id")] = None,
                         isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
                         name: str = None,
                         page: int = 1, pageSize: int = 20,
                         db: Session = Depends(get_sync_session)):
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
        if user_id is None or user_id == "":
            user_id_int = 0
        else:
            user_id_int = int(user_id)
        query_dict = {}
        if name is not None:
            query_dict["name"] = name
        data_sources, total = search_formatify_task(user_id_int, db, isadmin,query_dict, page, pageSize)
        return response_success(data={
            "list": data_sources,
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
async def delete_formatify(formatify_id: int, db: Session = Depends(get_sync_session)):
    """
    Delete a format conversion task
    Args:
        formatify_id (int): ID of the format conversion task to delete
        db (Session): Database session from dependency injection
    Returns:
        dict: Response indicating success or failure of deletion
    """
    try:
        result = delete_formatify_task(db, formatify_id)
        if not result:
            return response_fail(msg="Deletion failed")
        return response_success(data=result)
    except Exception as e:
        logger.error(f"delete_formatify: {str(e)}")
        return response_fail(msg=f"Deletion failed: {str(e)}")


def get_progress_from_mongodb_logs(task_uid: str) -> Optional[dict]:
    """
    从 MongoDB 日志中解析进度信息
    Args:
        task_uid: 任务唯一标识
    Returns:
        dict: 包含进度信息的字典，如果解析失败返回 None
    """
    try:
        if not task_uid:
            return None
        
        client = get_client()
        try:
            collection = get_formatity_collection(client, task_uid)
            
            # 查找包含进度信息的日志（按时间倒序）
            # 匹配格式：Updated and uploaded meta.json (total: X, success: Y, failure: Z)
            # 或：All files processed. Total: X, Success: Y, Failure: Z
            progress_patterns = [
                r'\(total:\s*(\d+),\s*success:\s*(\d+),\s*failure:\s*(\d+)\)',  # (total: X, success: Y, failure: Z)
                r'Total:\s*(\d+),\s*Success:\s*(\d+),\s*Failure:\s*(\d+)',  # Total: X, Success: Y, Failure: Z
            ]
            
            # 从最新的日志开始查找
            logs = collection.find({"level": "info"}).sort("create_at", -1).limit(100)
            
            for log in logs:
                content = log.get("content", "")
                if not content:
                    continue
                
                # 尝试匹配各种进度格式
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
                            "progress": progress
                        }
            
            # 如果没有找到进度信息，尝试查找 "Found X files to convert" 来获取总数
            logs_for_total = collection.find({"level": "info"}).sort("create_at", 1).limit(50)
            total_count = None
            for log in logs_for_total:
                content = log.get("content", "")
                # 匹配：Found X files to convert
                match = re.search(r'Found\s+(\d+)\s+files\s+to\s+convert', content, re.IGNORECASE)
                if match:
                    total_count = int(match.group(1))
                    break
            
            # 如果找到了总数，尝试统计成功和失败的数量
            if total_count is not None:
                success_count = 0
                failure_count = 0
                
                # 统计成功转换的日志
                success_logs = collection.find({
                    "level": "info",
                    "content": {"$regex": r"convert file.*succeed", "$options": "i"}
                })
                success_count = success_logs.count()
                
                # 统计失败的日志
                failure_logs = collection.find({
                    "level": "error",
                    "content": {"$regex": r"convert file.*error", "$options": "i"}
                })
                failure_count = failure_logs.count()
                
                processed = success_count + failure_count
                progress = round(processed / max(total_count, 1) * 100, 2) if total_count > 0 else 0
                
                return {
                    "total": total_count,
                    "success": success_count,
                    "failure": failure_count,
                    "progress": progress
                }
                
        finally:
            client.close()
            
    except Exception as e:
        logger.warning(f"Failed to get progress from MongoDB logs: {str(e)}")
        return None
    
    return None


@router.get("/formatify/get/{formatify_id}", response_model=dict)
async def get_formatify(formatify_id: int, db: Session = Depends(get_sync_session)):
    """
    Get details of a specific format conversion task
    Args:
        formatify_id (int): ID of the format conversion task to retrieve
        db (Session): Database session from dependency injection
    Returns:
        dict: Response with task details and progress information
    """
    try:
        result = get_formatify_task(db, formatify_id)
        if not result:
            return response_fail(msg="Query failed")
        
        task_dict = result.to_dict()
        
        # 如果任务正在执行、已完成或失败，尝试从 MongoDB 日志中解析进度信息
        # 即使任务失败，日志中也可能有进度信息，应该显示给用户
        if result.task_status in [DataFormatTaskStatusEnum.EXECUTING.value, DataFormatTaskStatusEnum.COMPLETED.value, DataFormatTaskStatusEnum.ERROR.value]:
            if result.task_uid:
                progress_info = get_progress_from_mongodb_logs(task_uid=result.task_uid)
                if progress_info:
                    task_dict["progress"] = progress_info
        
        return response_success(data=task_dict)
    except Exception as e:
        logger.error(f"get_formatify: {str(e)}")
        return response_fail(msg=f"Query failed: {str(e)}")


# Stop task
@router.post("/formatify/stop/{formatify_id}", response_model=dict)
async def stop_formatify(formatify_id: int, db: Session = Depends(get_sync_session)):
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
        if formatify_task.task_status != DataFormatTaskStatusEnum.EXECUTING.value:
            return response_fail(msg="Task execution has already ended")
        result, msg = stop_formatify_task(db, formatify_task)
        if result:
            return response_success(data="Task stopped successfully")
        return response_fail(msg="Task stop failed: " + msg)
    except Exception as e:
        logger.error(f"stop_formatify: {str(e)}")
        return response_fail(msg=f"Stop failed: {str(e)}")
