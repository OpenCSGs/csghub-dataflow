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
                                          get_celery_worker_key)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
# 禁用 APScheduler 的日志（只显示错误）
logging.getLogger('apscheduler').setLevel(logging.ERROR)

sys.path.append(str(Path(__file__).resolve().parent.parent))
# 2、指定briker，用于存放提交的异步任务
broker = f'{get_radis_database_uri()}/0'
# 3、指定backend，用于存放函数执行结束的结果
backend = f'{get_radis_database_uri()}/1'

celery_scheduler = BackgroundScheduler()

# 存30分钟
celery_app = Celery('data-flow-celery', broker=broker, backend=backend,result_expires=60 * 1)

print(f"启动路径:{os.getcwd()}")

celery_app.autodiscover_tasks([
                                'data_celery.test01',
                                'data_celery.datasource.mysql',
                                'data_celery.datasource.mongo',
                                'data_celery.datasource.hive',
                                'data_celery.formatify',
                                'data_celery.job',
                               ])

# Beat 配置
celery_app.conf.beat_schedule = {
    'celery_pipline_status': {
        'task': 'celery_pipline_status_task',  # 监控pipline 运行状态
        'schedule': 10.0,  # 定时任务的间隔时间（秒）
        'args': (),
    },
    'celery_server_status': {
        'task': 'celery_server_status_task',  # 监控celery 负载均衡部署设备运行状态
        'schedule': 1.5,  # 定时任务的间隔时间（秒）
        'args': (),
    },
}

celery_app.conf.timezone = 'Asia/Shanghai'
@worker_ready.connect
def on_celery_worker_ready(sender,**kwargs):
    try:
        worker_name = getattr(sender, 'hostname', None)
        if worker_name:
            redis_celery = get_celery_worker_redis_db()
            redis_key = get_celery_worker_key()
            all_elements = redis_celery.lrange(redis_key, 0, -1)  # 0 到 -1 表示所有元素
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
                trigger=IntervalTrigger(seconds=2),  # 每2秒执行一次
                id='celery_server_status_task',
                name='celery_server_status_task Task',
                replace_existing=True,
                args=(worker_name,),  # 传递位置参数
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



def celery_server_status_task(worker_name):
    """
    定时检测celery服务的状态
    """
    try:
        # logger.info("定时检测celery服务的状态 start")
        current_time = get_timestamp()
        task_count = get_current_task_count(worker_name)
        current_ip = get_current_ip()
        celery_server_status = {
            "worker_name": worker_name,
            "current_time": current_time,
            "task_count": task_count,
            "current_ip": current_ip
        }
        set_celery_server_status(worker_name,json.dumps(celery_server_status),10)

    except Exception as e:
        logger.error(f"celery_server_status_task error:{e}")

def get_current_task_count(worker_name:str):
    """
    获取当前worker的运行中的任务数量
    """
    # i = celery_app.control.inspect()
    # active_tasks = i.active()
    # task_count = 0
    # if active_tasks:
    #     for worker, tasks in active_tasks.items():
    #         if  worker == worker_name:
    #             task_count = len(tasks)
    #             return task_count
    # return task_count
    # TODO:获取pipline 任务数量，根据执行时写入的 process id  list 来读取count
    return 0