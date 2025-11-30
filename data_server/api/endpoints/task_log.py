from fastapi import APIRouter

from data_celery.mongo_tools.tools import get_log_List
from data_server.schemas.responses import response_success

router = APIRouter()


@router.get("/list", response_model=dict)
async def get_list(
        task_uid: str,
        type: str,
        page: int = 1,
        page_size: int = 10,
        level: str = None):


    log_list = get_log_List(task_uid=task_uid, page=page, page_size=page_size, level=level, type=type)

    return response_success(data=log_list)

