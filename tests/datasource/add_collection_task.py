from data_server.datasource.DatasourceModels import DataSource, CollectionTask,DataSourceTaskStatusEnum
from data_server.database.session import get_sync_session
from sqlalchemy.orm import Session
from data_server.datasource.DatasourceManager import execute_collection_task
from data_server.datasource.DatasourceTask import run_celery_task,stop_celery_task
import uuid,os
from data_server.utils.auth import intercept_web_token, get_user_token, TokenExpiredError, TokenNotFoundError

def greate_task_uid():

    return str(uuid.uuid4())
def add_new_collection_task():
    db_session: Session = get_sync_session()
    datasource_id = 0
    user_name = 'z275748353'


    user_token = intercept_web_token(user_name)
    if not user_token:

        try:
            user_token = get_user_token(user_name)
        except (TokenExpiredError, TokenNotFoundError) as e:
            raise Exception(f"获取用户token失败: {str(e)}")
    data_source = db_session.query(DataSource).get(datasource_id)
    task_uid = greate_task_uid()
    collection_task = CollectionTask(task_uid=task_uid,
                                     datasource_id=datasource_id,
                                     task_status=DataSourceTaskStatusEnum.WAITING.value,
                                     total_count=0,
                                     records_count=0)

    task_celery_uid = run_celery_task(data_source, task_uid, user_name, user_token)
    collection_task.task_celery_uid = task_celery_uid
    collection_task.task_status = DataSourceTaskStatusEnum.EXECUTING.value
    db_session.commit()


def run_old_collection_task():
    db_session: Session = get_sync_session()
    collection_task_id = 0
    user_name = 'z275748353'


    user_token = intercept_web_token(user_name)
    if not user_token:

        try:
            user_token = get_user_token(user_name)
        except (TokenExpiredError, TokenNotFoundError) as e:
            raise Exception(f"获取用户token失败: {str(e)}")
    collection_task = db_session.query(CollectionTask).get(collection_task_id)
    execute_collection_task(collection_task, user_name, user_token)

if __name__ == '__main__':

    add_new_collection_task()

    # run_old_collection_task()