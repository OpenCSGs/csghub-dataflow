from data_celery.main import celery_app
from loguru import logger
import time


@celery_app.task(name="collection_file_task")
def collection_file_task(task_uid: str,user_name: str,user_token: str):
    """
    采集任务
    Args:
        task_uid (str): 任务UID
        user_name (str): 用户名称
        user_token (str): 用户token
    Returns:
        bool: 执行操作是否成功
    """
    #TODO: file导入 真正执行任务
    return True