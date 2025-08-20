from sqlalchemy.orm import Session
from data_server.formatify.FormatifyModels import DataFormatTask, DataFormatTaskStatusEnum
from data_server.formatify.schemas import DataFormatTaskRequest
import uuid, os
from typing import List, Tuple, Optional
from data_server.formatify.FormatifyTask import run_format_task, stop_celery_task


def greate_task_uid():

    return str(uuid.uuid4())


def create_formatify_task(db_session: Session, dataFormatTask: DataFormatTaskRequest, user_id, user_name: str,
                          user_token: str):

    # create db model
    task_uid = greate_task_uid()
    data_format_task_db = DataFormatTask(name=dataFormatTask.name,
                                         des=dataFormatTask.des,
                                         from_csg_hub_dataset_name=dataFormatTask.from_csg_hub_dataset_name,
                                         from_csg_hub_dataset_id=dataFormatTask.from_csg_hub_dataset_id,
                                         from_csg_hub_dataset_branch=dataFormatTask.from_csg_hub_dataset_branch,
                                         from_data_type=dataFormatTask.from_data_type,
                                         from_csg_hub_repo_id=dataFormatTask.from_csg_hub_repo_id,
                                         to_csg_hub_dataset_name=dataFormatTask.to_csg_hub_dataset_name,
                                         to_csg_hub_dataset_id=dataFormatTask.to_csg_hub_dataset_id,
                                         to_csg_hub_dataset_default_branch=dataFormatTask.to_csg_hub_dataset_default_branch,
                                         to_csg_hub_repo_id=dataFormatTask.to_csg_hub_repo_id,
                                         to_data_type=dataFormatTask.to_data_type,
                                         task_uid=task_uid,
                                         task_status=DataFormatTaskStatusEnum.WAITING.value,
                                         owner_id=user_id)

    db_session.add(data_format_task_db)
    db_session.commit()
    # print(100*'*')
    task_celery_uid = run_format_task(data_format_task_db.id, user_name, user_token)
    data_format_task_db.task_celery_uid = task_celery_uid
    data_format_task_db.task_status = DataFormatTaskStatusEnum.EXECUTING.value
    db_session.commit()
    return data_format_task_db.id


def search_formatify_task(
        user_id: int,
        session: Session,
        isadmin: bool = False,
        query_dict = None,
        page: int = 1,
        per_page: int = 10
) -> Tuple[List[DataFormatTask], int]:


    query = session.query(DataFormatTask)
    if not isadmin:
        query = query.filter(DataFormatTask.owner_id == user_id)
    if query_dict:
        if query_dict['name']:
            query = query.filter(DataFormatTask.name.like(f"%{query_dict['name']}%"))

    total_count = query.count()

    data_format_tasks = query.order_by(DataFormatTask.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    data_format_tasks = [task.to_dict() for task in data_format_tasks]
    return data_format_tasks, total_count


def update_formatify_task(db_session: Session, formatify_id: int, dataFormatTaskRequest: DataFormatTaskRequest):

    formatify_task: DataFormatTask = db_session.query(DataFormatTask).get(formatify_id)
    if formatify_task is None:
        return None
    updatable_fields = {
        'name', 'des', 'from_csg_hub_dataset_name', 'from_csg_hub_dataset_id',
        'from_csg_hub_dataset_branch', 'from_data_type', 'to_csg_hub_dataset_name',
        'to_csg_hub_dataset_id', 'to_csg_hub_dataset_default_branch', 'to_data_type'
    }
    for field in updatable_fields:
        value = getattr(dataFormatTaskRequest, field, None)
        if value is not None and value != '':
            setattr(formatify_task, field, value)

    db_session.commit()
    return formatify_task.to_dict()



def delete_formatify_task(db_session: Session, formatify_id: int):


    #
    formatify_task = db_session.query(DataFormatTask).get(formatify_id)
    if formatify_task is None:
        return False

    db_session.delete(formatify_task)
    db_session.commit()
    return True



def get_formatify_task(db_session: Session, formatify_id: int):

    formatify_task = db_session.query(DataFormatTask).get(formatify_id)
    return formatify_task


def stop_formatify_task(db_session: Session, formatify_task: DataFormatTask):

    try:
        result = stop_celery_task(formatify_task.task_celery_uid)
        if result:
            formatify_task.task_status = DataFormatTaskStatusEnum.STOP.value
            db_session.commit()
        else:
            return False, "结束任务异常"
        return True, None
    except Exception as e:
        print(f"执行任务失败: {str(e)}")
        return False, str(e)
