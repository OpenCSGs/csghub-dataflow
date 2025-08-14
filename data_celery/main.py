# utf-8

from celery import Celery
from celery.signals import worker_ready,worker_shutdown
from celery.schedules import crontab, timedelta
from data_celery.utils import get_current_ip,get_timestamp
from data_celery.redis_tools.tools import set_celery_server_status
from loguru import logger
import os,sys,json
from pathlib import Path
from data_server.database.session import (get_radis_database_uri,get_celery_worker_redis_db,
                                          get_celery_worker_key,get_celery_process_list_key,
                                          get_celery_kill_process_list_key,get_celery_task_process_resource_key)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging,platform,psutil


logging.getLogger('apscheduler').setLevel(logging.ERROR)

sys.path.append(str(Path(__file__).resolve().parent.parent))

broker = f'{get_radis_database_uri()}/0'

backend = f'{get_radis_database_uri()}/1'

celery_scheduler = BackgroundScheduler()


celery_app = Celery('data-flow-celery', broker=broker, backend=backend,result_expires=60 * 1 * 12)

print(f"启动路径:{os.getcwd()}")

celery_app.autodiscover_tasks([
                                'data_celery.test01',
                                'data_celery.datasource.mysql',
                                'data_celery.datasource.mongo',
                                'data_celery.datasource.hive',
                                'data_celery.formatify',
                                'data_celery.job',
                               ])


celery_app.conf.beat_schedule = {
    'celery_pipline_status': {
        'task': 'celery_pipline_status_task',
        'schedule': 10.0,
        'args': (),
    },
    'celery_server_status': {
        'task': 'celery_server_status_task',
        'schedule': 1.5,
        'args': (),
    },
}

celery_app.conf.timezone = 'Asia/Shanghai'
celery_app.conf.enable_utc = False
@worker_ready.connect
def on_celery_worker_ready(sender,**kwargs):
    try:
        worker_name = getattr(sender, 'hostname', None)
        if worker_name:
            redis_celery = get_celery_worker_redis_db()
            redis_key = get_celery_worker_key()
            all_elements = redis_celery.lrange(redis_key, 0, -1)
            real_key = worker_name
            if real_key not in [str(element) for element in all_elements]:
                redis_celery.rpush(redis_key, real_key)
            logger.info(f"{real_key} - celery 启动成功")
            current_ip = get_current_ip()
            celery_server_status = {
                "worker_name": worker_name,
                "current_time": get_timestamp(),
                "task_count": 0,
                "current_ip": current_ip
            }
            set_celery_server_status(worker_name, json.dumps(celery_server_status), 12)

            celery_scheduler.add_job(
                func=celery_server_status_task,
                trigger=IntervalTrigger(seconds=2),
                id='celery_server_status_task',
                name='celery_server_status_task Task',
                replace_existing=True,
                args=(worker_name,current_ip),
            )

            celery_scheduler.add_job(
                func=celery_pipline_kill_process_task,
                trigger=IntervalTrigger(seconds=5),
                id='celery_pipline_kill_process_task',
                name='celery_pipline_kill_process_task Task',
                replace_existing=True,
                args=(worker_name, current_ip),
            )
            celery_scheduler.add_job(
                func=get_process_resource_usage_task,
                trigger=IntervalTrigger(seconds=3),
                id='get_process_resource_usage_task',
                name='get_process_resource_usage_task Task',
                replace_existing=True,
                args=(worker_name, current_ip),
            )
            celery_scheduler.start()
        else:
            raise ValueError("celery 启动失败")
    except Exception as e:
        logger.error(f"{get_current_ip()} - celery 启动失败 ：{e}")


@worker_shutdown.connect
def on_celery_worker_shutdown(sender,**kwargs):
    try:
        logger.info(f"{sender.hostname} - celery 停止")
    except Exception as e:
        logger.error(f"{get_current_ip()} - celery 停止失败 ：{e}")



def celery_server_status_task(worker_name,current_ip):
    try:

        current_time = get_timestamp()
        task_count = get_current_task_count(worker_name,current_ip)

        celery_server_status = {
            "worker_name": worker_name,
            "current_time": current_time,
            "task_count": task_count,
            "current_ip": current_ip
        }
        set_celery_server_status(worker_name,json.dumps(celery_server_status),12)

    except Exception as e:
        logger.error(f"celery_server_status_task error:{e}")

def get_current_task_count(worker_name:str,current_ip:str):
    # i = celery_app.control.inspect()
    # active_tasks = i.active()
    # task_count = 0
    # if active_tasks:
    #     for worker, tasks in active_tasks.items():
    #         if  worker == worker_name:
    #             task_count = len(tasks)
    #             return task_count
    # return task_count
    redis_process_key = get_celery_process_list_key(worker_name, current_ip)
    redis_celery = get_celery_worker_redis_db()
    all_elements = redis_celery.lrange(redis_process_key, 0, -1)
    if all_elements:
        return len(all_elements)
    return 0


def celery_pipline_kill_process_task(worker_name:str,current_ip:str):
    try:

        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_kill_process_list_key(worker_name,current_ip)

        while redis_celery.llen(redis_key) > 0:
            process_id = redis_celery.lpop(redis_key)
            if process_id and process_id != "":
                kill_process(process_id)
    except Exception :
        pass

def kill_process(process_id):
    """
    kill process
    """
    try:
        process_id_int = int(process_id)
        os.system(f"kill -9 {process_id_int}")
        if platform.system() == "Windows":
            os.system(f"taskkill /PID {process_id_int} /F")
        elif platform.system() == "Linux":
            os.system(f"kill -9 {process_id_int}")
    except Exception as e:
        return


def get_process_resource_usage_task(worker_name:str,current_ip:str):
    try:
        redis_process_key = get_celery_process_list_key(worker_name, current_ip)
        redis_celery = get_celery_worker_redis_db()
        all_elements = redis_celery.lrange(redis_process_key, 0, -1)
        for element in all_elements:
            process_id = element.split(":")[-1]
            job_uuid = element.split(":")[0]
            get_process_resource_usage(redis_celery,job_uuid,process_id)
    except Exception:
        pass

def get_process_resource_usage(redis_celery,job_uuid,process_id):
    try:

        process = psutil.Process(int(process_id))
        cpu_usage = process.cpu_percent(interval=1)

        memory_info = process.memory_info()
        memory_usage = memory_info.rss / (1024 * 1024)
        process_resource_key = get_celery_task_process_resource_key(job_uuid)
        status_json = {
            "job_uuid": job_uuid,
            "process_id": process_id,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage
        }
        redis_celery.set(process_resource_key, status_json, 8)
    except Exception:
        pass