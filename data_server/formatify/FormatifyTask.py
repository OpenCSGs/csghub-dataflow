from celery.result import AsyncResult

from data_celery.formatify.tasks import format_task
from data_celery.main import celery_app

def run_format_task(task_id: int,user_name:str,user_token:str):

    task_celery = format_task.delay(task_id, user_name, user_token)
    return task_celery.id


def stop_celery_task(task_uid: str):

    task_result = AsyncResult(task_uid, app=celery_app)
    if not task_result:
        return False
    if task_result.status == 'STARTED' or task_result.status == 'PENDING' or task_result.status == 'RETRY':
        task_result.revoke(terminate=True)
        return True
    return False