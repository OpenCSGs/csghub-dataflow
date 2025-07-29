from data_celery.job.tasks import run_pipline_job
from celery.result import AsyncResult
from data_celery.main import celery_app

def run_pipline_task(task_uuid: str,user_id:int,user_name:str,user_token:str):
    task_celery = run_pipline_job.delay(task_uuid, user_id,user_name, user_token)
    return task_celery.id


def stop_celery_task(task_uid: str):
    """
    停止celery任务
    Args:
        task_uid (str): 任务UID
    Returns:
        bool: 执行操作是否成功
    """
    task_result = AsyncResult(task_uid, app=celery_app)
    if not task_result:
        return False
    if task_result.status == 'STARTED' or task_result.status == 'PENDING' or task_result.status == 'RETRY':
        task_result.revoke(terminate=True)
        # TODO:将对应的 host 记录 processid 清除掉 ，可以在清楚掉前，kill 进程 (放入一个即将杀死的进程队列，redis 使用host 地址分割数据)
        return True
    return False