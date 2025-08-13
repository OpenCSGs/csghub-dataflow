from data_celery.datasource.mysql.tasks import collection_mysql_task
from data_celery.datasource.mongo.tasks import collection_mongo_task
from data_celery.datasource.hive.tasks import collection_hive_task
from data_celery.datasource.file.tasks import collection_file_task
from data_server.datasource.DatasourceModels import (DataSource, DataSourceTypeEnum, CollectionTask)
from celery.result import AsyncResult
from loguru import logger
from data_celery.main import celery_app
from data_server.utils.datetime_utils import parse_shanghai_datetime
def run_celery_task(data_source_db: DataSource, task_uid: str, user_name: str, user_token: str):
    """
    Run celery task
    Args:
        data_source_db (DataSource): Data source
        task_uid (str): Task UID
    Returns:
        bool: Whether the execution operation is successful
    """
    if data_source_db.source_type == DataSourceTypeEnum.MYSQL.value:
        task = collection_mysql_task
    elif data_source_db.source_type == DataSourceTypeEnum.MONGODB.value:
        task = collection_mongo_task
    elif data_source_db.source_type == DataSourceTypeEnum.HIVE.value:
        task = collection_hive_task
    elif data_source_db.source_type == DataSourceTypeEnum.FILE.value:
        task = collection_file_task
    else:
        raise ValueError("Unknown source type")
    if data_source_db.task_run_time is not None:
        logger.info(f'Delay task execution：{task_uid}，时间：{data_source_db.task_run_time}, user_name: {user_name}, user_token: {user_token}')
        task_celery = task.apply_async(args=[task_uid, user_name, user_token], eta=parse_shanghai_datetime(data_source_db.task_run_time))
    else:
        logger.info(f'Task execution：{task_uid}, Execute immediately, user_name: {user_name}, user_token: {user_token}')
        task_celery = task.delay(task_uid, user_name, user_token)
    return task_celery.id


def stop_celery_task(task_uid: str):
    """
    Stop celery task
    Args:
        task_uid (str): Task UID
    Returns:
        bool: Whether the execution operation is successful
    """
    try:
        task_result = AsyncResult(task_uid, app=celery_app)
        if not task_result:
            return False

        logger.info(f"Task {task_uid} current status: {task_result.status}")


        if task_result.status in ['PENDING', 'RECEIVED', 'STARTED', 'RETRY']:

            task_result.revoke(terminate=True, signal='SIGTERM')
            logger.info(f"Sent revoke signal to task {task_uid}")
            return True
        else:
            logger.info(f"Task {task_uid} cannot be revoked in {task_result.status} status")
            return False
    except Exception as e:
        logger.error(f"Error stopping task {task_uid}: {e}")
        return False

