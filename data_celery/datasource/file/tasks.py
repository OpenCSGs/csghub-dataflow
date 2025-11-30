from data_celery.main import celery_app
from loguru import logger
import time


@celery_app.task(name="collection_file_task")
def collection_file_task(task_uid: str,user_name: str,user_token: str):


    return True