from fastapi import FastAPI, APIRouter, HTTPException, status, Header, Depends
from oauthlib.uri_validate import query
from sqlalchemy.orm import Session
from typing import Annotated, Union
from loguru import logger
from data_server.database.session import get_sync_session
from data_server.schemas.responses import response_success, response_fail
from data_server.formatify.FormatifyModels import DataFormatTypeEnum, DataFormatTaskStatusEnum, DataFormatTask
from data_server.formatify.schemas import DataFormatTaskRequest
from data_server.formatify.FormatifyManager import (create_formatify_task, search_formatify_task,
                                                    update_formatify_task, delete_formatify_task,
                                                    get_formatify_task, stop_formatify_task)
from sqlalchemy import func
router = APIRouter()


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
                                    user_id: Annotated[str | None, Header(alias="user_id")] = None,
                                    user_name: Annotated[str | None, Header(alias="user_name")] = None,
                                    user_token: Annotated[str | None, Header(alias="user_token")] = None
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
async def formatify_list(user_id: Annotated[str | None, Header(alias="user_id")] = None,
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


@router.get("/formatify/get/{formatify_id}", response_model=dict)
async def get_formatify(formatify_id: int, db: Session = Depends(get_sync_session)):
    """
    Get details of a specific format conversion task
    Args:
        formatify_id (int): ID of the format conversion task to retrieve
        db (Session): Database session from dependency injection
    Returns:
        dict: Response with task details or failure message
    """
    try:
        result = get_formatify_task(db, formatify_id)
        if not result:
            return response_fail(msg="Query failed")
        return response_success(data=result.to_dict())
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
