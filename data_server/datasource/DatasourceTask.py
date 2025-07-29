from data_celery.datasource.mysql.tasks import collection_mysql_task
from data_celery.datasource.mongo.tasks import collection_mongo_task
from data_celery.datasource.hive.tasks import collection_hive_task
from data_celery.datasource.file.tasks import collection_file_task
from data_server.datasource.DatasourceModels import (DataSource, DataSourceTypeEnum, CollectionTask)
from celery.result import AsyncResult
from loguru import logger
from data_celery.main import celery_app
def run_celery_task(data_source_db: DataSource, task_uid: str, user_name: str, user_token: str):
    """
    运行celery任务
    Args:
        data_source_db (DataSource): 数据源
        task_uid (str): 任务UID
    Returns:
        bool: 执行操作是否成功
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
        logger.info(f'延时执行任务：{task_uid}，时间：{data_source_db.task_run_time}, user_name: {user_name}, user_token: {user_token}')
        task_celery = task.apply_async(args=[task_uid, user_name, user_token], eta=data_source_db.task_run_time)
    else:
        logger.info(f'执行任务：{task_uid}, 立即执行, user_name: {user_name}, user_token: {user_token}')
        task_celery = task.delay(task_uid, user_name, user_token)
    return task_celery.id


def stop_celery_task(task_uid: str):
    """
    停止celery任务
    Args:
        task_uid (str): 任务UID
    Returns:
        bool: 执行操作是否成功
    """
    try:
        task_result = AsyncResult(task_uid, app=celery_app)
        if not task_result:
            return False

        # 打印当前任务状态用于调试
        logger.info(f"Task {task_uid} current status: {task_result.status}")

        # 检查更多可能需要终止的状态
        # 包括 'RECEIVED' 状态的任务
        if task_result.status in ['PENDING', 'RECEIVED', 'STARTED', 'RETRY']:
            # 发送终止信号
            task_result.revoke(terminate=True, signal='SIGTERM')
            logger.info(f"Sent revoke signal to task {task_uid}")
            return True
        else:
            logger.info(f"Task {task_uid} cannot be revoked in {task_result.status} status")
            return False
    except Exception as e:
        logger.error(f"Error stopping task {task_uid}: {e}")
        return False

