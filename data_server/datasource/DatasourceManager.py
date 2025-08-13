import time

from data_server.datasource.DatasourceModels import (DataSource, CollectionTask,
                                                     DataSourceTaskStatusEnum, DataSourceTypeEnum,
                                                     DataSourceStatusEnum)
from data_server.datasource.schemas import DataSourceCreate, DataSourceUpdate
from data_server.database.session import get_sync_session
from sqlalchemy.orm import Session
from data_server.datasource.DatasourceTask import run_celery_task, stop_celery_task
import json
from typing import List, Tuple, Optional
import uuid, os
from data_celery.utils import get_datasource_log_path
from loguru import logger


def greate_task_uid():
    """
    Generate a task UID
    Returns:
        str: The generated task UID
    """
    return str(uuid.uuid4())


def create_data_source(is_connection: bool, db_session: Session, datasource: DataSourceCreate, user_id, user_name: str,
                       user_token: str):
    """
    Create a data source
    Args:
        datasource (DataSourceCreate): Data source creation parameters
        user_id (int): User ID
        user_name (str): User name
        user_token (str): User token
    Returns:
        int: ID of the created data source
    """
    # create db model
    data_source_db = DataSource(name=datasource.name,
                                des=datasource.des,
                                source_type=datasource.source_type,
                                host=datasource.host,
                                port=datasource.port,
                                username=datasource.username,
                                password=datasource.password,
                                database=datasource.database,
                                task_run_time=datasource.task_run_time,
                                extra_config=json.dumps(datasource.extra_config, ensure_ascii=False, indent=4))
    data_source_db.source_status = datasource.source_status
    data_source_db.owner_id = user_id
    db_session.add(data_source_db)
    db_session.commit()
    if datasource.is_run:
        logger.info(f"DataSource{datasource.name} Start executing the task")

        task_uid = greate_task_uid()
        collection_task = CollectionTask(task_uid=task_uid,
                                         datasource_id=data_source_db.id,
                                         task_status=DataSourceTaskStatusEnum.WAITING.value,
                                         total_count=0,
                                         records_count=0)
        db_session.add(collection_task)
        db_session.commit()

        task_celery_uid = run_celery_task(data_source_db, task_uid, user_name, user_token)
        collection_task.task_celery_uid = task_celery_uid
        collection_task.task_status = DataSourceTaskStatusEnum.WAITING.value
        db_session.commit()
        if is_connection:
            data_source_db.source_status = DataSourceStatusEnum.ACTIVE.value
        else:
            data_source_db.source_status = DataSourceStatusEnum.INACTIVE.value
        db_session.commit()
    return data_source_db.id


def search_data_source(
        user_id: int,
        session: Session,
        isadmin: bool = False,
        page: int = 1,
        per_page: int = 10,
        name: str = None,
        source_type=None
) -> Tuple[List[DataSource], int]:
    """
    Search data sources

    Args:
        user_id (int): User ID
        session (Session): Database session
        isadmin (bool): Whether the user is an administrator
        page (int): Current page number, default is 1
        per_page (int): Number of items displayed per page, default is 10

    Returns:
        Tuple[List[DataSource], int]: The first element is the list of searched data sources, the second element is the total number of records
    """

    query = session.query(DataSource)
    if not isadmin:
        query = query.filter(DataSource.owner_id == user_id)
    if name is not None:
        query = query.filter(DataSource.name.like(f"%{name}%"))
    if source_type is not None:
        query = query.filter(DataSource.source_type == source_type)

    total_count = query.count()

    data_sources = query.order_by(DataSource.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return data_sources, total_count


def update_data_source(db_session: Session, data_source_id: int, update_data: DataSourceUpdate):
    """
    Update data source record

    Args:
        db_session (Session): Database session
        data_source_id (int): ID of the data source to be updated
        update_data (DataSourceUpdate): Update data

    Returns:
        Optional[DataSource]: The updated data source object, or None if not found
    """

    data_source = db_session.query(DataSource).get(data_source_id)
    if data_source is None:
        return None

    if update_data.name is not None:
        data_source.name = update_data.name
    if update_data.host is not None:
        data_source.host = update_data.host
    if update_data.port is not None:
        data_source.port = update_data.port
    if update_data.username is not None:
        data_source.username = update_data.username
    if update_data.password is not None:
        data_source.password = update_data.password
    if update_data.database is not None:
        data_source.database = update_data.database
    if update_data.extra_config is not None:
        data_source.extra_config = json.dumps(update_data.extra_config, ensure_ascii=False, indent=4)
    db_session.commit()

    return data_source


def delete_data_source(db_session: Session, data_source_id: int):
    """
    Delete data source record
    Args:
        db_session (Session): Database session
        data_source_id (int): ID of the data source to be deleted
    Returns:
        bool: Whether the deletion operation is successful
    """

    db_session.query(CollectionTask).filter_by(datasource_id=data_source_id).delete()

    data_source = db_session.query(DataSource).get(data_source_id)
    if data_source is None:
        return False

    db_session.delete(data_source)
    db_session.commit()
    return True


def get_datasource(db_session: Session, datasource_id: int):
    """
    Get data source information
    Args:
        db_session (Session): Database session
        datasource_id (int): Data source ID
    Returns:
        DataSource: Data source object
    """
    data_source = db_session.query(DataSource).get(datasource_id)
    return data_source


def has_execting_tasks(db_session: Session, datasource_id: int):
    """
    Check if the data source has running tasks
    Args:
        db_session (Session): Database session
        datasource_id (int): Data source ID
    Returns:
        bool: Whether there are running tasks
    """
    query = db_session.query(CollectionTask).filter_by(datasource_id=datasource_id,
                                                       task_status=DataSourceTaskStatusEnum.EXECUTING.value).exists()
    return db_session.query(query).scalar()


def get_collection_task(db_session: Session, task_id: int):
    """
    Get collection task information
    Args:
        db_session (Session): Database session
        task_id (int): Task ID
    Returns:
        CollectionTask: Collection task object
    """
    collection_task = db_session.query(CollectionTask).get(task_id)
    return collection_task


def get_collection_task_by_uid(db_session: Session, task_uid: str):
    """
    Get unique collection task information by task UID

    Args:
        db_session (Session): Database session
        task_uid (str): Task UID

    Returns:
        CollectionTask: Unique collection task object, or None if it does not exist
    """

    collection_task = db_session.query(CollectionTask).filter(CollectionTask.task_uid == task_uid).one_or_none()
    return collection_task


def search_collection_task(
        datasource_id: int,
        session: Session,
        page: int = 1,
        per_page: int = 10
) -> Tuple[List[CollectionTask], int]:
    """
    Search the list of tasks under a data source
    Args:
        datasource_id (int): Data source ID
        session (Session): Database session
        page (int): Current page number, default is 1
        per_page (int): Number of items displayed per page, default is 10

    Returns:
        Tuple[List[CollectionTask], int]: The first element is the list of searched data source tasks, the second element is the total number of records
    """
    query = session.query(CollectionTask).filter_by(datasource_id=datasource_id)
    total_count = query.count()
    collection_tasks = query.order_by(CollectionTask.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return collection_tasks, total_count


def search_collection_task_all(
        datasource_id: int,
        session: Session,
) -> Tuple[List[CollectionTask], int]:
    """
    Search the list of tasks under a data source
    Args:
        datasource_id (int): Data source ID
        session (Session): Database session
    Returns:
        Tuple[List[CollectionTask], int]: The first element is the list of searched data source tasks, the second element is the total number of records
    """
    query = session.query(CollectionTask).filter_by(datasource_id=datasource_id)

    total_count = query.count()

    collection_tasks = query.order_by(CollectionTask.created_at).all()
    return collection_tasks, total_count


def execute_collection_task(db_session: Session, collection_task: CollectionTask, user_name: str, user_token: str):
    """
    Execute a task
    Args:
        db_session (Session): Database session
        collection_task (CollectionTask): Task object
        user_name (str): User name
        user_token (str): User token
    Returns:
        bool: Whether the execution operation is successful
    """
    try:
        if not collection_task.datasource:
            return False, "Data source does not exist"
        task_celery_uid = run_celery_task(collection_task.datasource, collection_task.task_uid, user_name, user_token)
        if task_celery_uid is None:
            return False, "Incorrect data source type"
        collection_task.task_celery_uid = task_celery_uid
        db_session.commit()
        return True, None
    except Exception as e:
        print(f"Execution of the task failed: {str(e)}")
        return False, str(e)


def stop_collection_task(db_session: Session, collection_task: CollectionTask):
    """
    Execute a task
    Args:
        db_session (Session): Database session
        collection_task (CollectionTask): Task object
    Returns:
        bool: Whether the execution operation is successful
    """
    try:
        if not collection_task.datasource:
            return False, "Data source does not exist"
        result = stop_celery_task(collection_task.task_celery_uid)
        if result:
            collection_task.task_status = DataSourceTaskStatusEnum.STOP.value
            db_session.commit()
        else:
            return False, "Abnormal termination of the task"
        return True, None
    except Exception as e:
        print(f"Task execution failed: {str(e)}")
        return False, str(e)


def execute_new_collection_task(db_session: Session, datasource: DataSource, user_name: str, user_token: str):
    """
    Execute a task
    Args:
        db_session (Session): Database session
        datasource (DataSource): Data source
        user_name (str): User name
        user_token (str): User token
    Returns:
        bool: Whether the execution operation is successful
    """
    try:

        task_uid = greate_task_uid()
        collection_task = CollectionTask(task_uid=task_uid,
                                         datasource_id=datasource.id,
                                         task_status=DataSourceTaskStatusEnum.WAITING.value,
                                         total_count=0,
                                         records_count=0)
        db_session.add(collection_task)
        db_session.commit()
        task_celery_uid = run_celery_task(datasource, task_uid, user_name, user_token)
        if task_celery_uid is None:
            return False, "Incorrect data source type"
        collection_task.task_celery_uid = task_celery_uid
        collection_task.task_status = DataSourceTaskStatusEnum.WAITING.value
        db_session.commit()
        return True, None
    except Exception as e:
        print(f"Task execution failed: {str(e)}")
        return False, str(e)


def read_task_log(collection_task: CollectionTask):
    """
    Read task log
    Args:
        collection_task (CollectionTask): Task object
    Returns:
        str: Task log
    """
    log_file_path = get_datasource_log_path(collection_task.task_uid)
    try:
        with open(log_file_path, 'r') as f:
            file_content = f.read()
        return True, file_content
    except Exception as e:
        print(f"Failed to query logs: {str(e)}")
        return False, str(e)
