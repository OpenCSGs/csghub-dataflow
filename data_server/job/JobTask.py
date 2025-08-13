from data_celery.job.tasks import run_pipline_job
from celery.result import AsyncResult
from data_celery.main import celery_app
from data_server.database.session import get_celery_kill_process_list_key, get_celery_task_process_real_key,get_celery_worker_redis_db
from datetime import datetime
from data_server.utils.datetime_utils import parse_shanghai_datetime


def run_pipline_task(task_uuid: str,user_id:int,user_name:str,user_token:str,task_run_time:datetime):
    if task_run_time is not None:
        task_celery = run_pipline_job.apply_async(args=[task_uuid, user_id,user_name, user_token],
                                       eta=parse_shanghai_datetime(task_run_time))
        return task_celery.id
    else:
        task_celery = run_pipline_job.delay(task_uuid, user_id,user_name, user_token)
        return task_celery.id


def stop_celery_task(task_uid: str,task_celery_uid:str,run_celery_host:str,celery_worker_name:str):
    task_result = AsyncResult(task_celery_uid, app=celery_app)
    if not task_result:
        return False

    redis_celery = get_celery_worker_redis_db()
    celery_task_process_real_key = get_celery_task_process_real_key(task_uid)
    process_id = redis_celery.get(celery_task_process_real_key)
    if process_id is None and process_id != "":
        try:
            # 添加到 kill redis 列表
            celery_task_kill_list_key = get_celery_kill_process_list_key(celery_worker_name,run_celery_host)
            redis_celery.rpush(celery_task_kill_list_key, process_id)
        except:
            pass
    if task_result.status == 'STARTED' or task_result.status == 'PENDING' or task_result.status == 'RETRY':
        task_result.revoke(terminate=True)
        return True
    return False