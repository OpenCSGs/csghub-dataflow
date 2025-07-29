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
    """
    获取日志列表接口
    Args:
        task_uid (str): 任务唯一标识符
        type (str): 日志类型（采集任务：datasource,格式转换任务：formatity
        page (int, optional): 页码，默认为1
        page_size (int, optional): 每页大小，默认为10
        level (str, optional): 日志级别，默认为None
    """
    # 查询日志列表数据
    log_list = get_log_List(task_uid=task_uid, page=page, page_size=page_size, level=level, type=type)
    # 返回成功响应结果
    return response_success(data=log_list)

