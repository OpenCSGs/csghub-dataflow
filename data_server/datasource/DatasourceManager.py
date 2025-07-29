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
    生成任务UID
    Returns:
        str: 生成的任务UID
    """
    return str(uuid.uuid4())


def create_data_source(is_connection: bool, db_session: Session, datasource: DataSourceCreate, user_id, user_name: str,
                       user_token: str):
    """
        创建数据源
        Args:
            datasource (DataSourceCreate): 数据源创建参数
            user_id (int): 用户ID
            user_name (str): 用户名称
            user_token (str): 用户令牌
        Returns:
            int: 创建的数据源ID
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
        logger.info(f"数据源{datasource.name}开始执行任务")
        # 如果符合添加，执行采集 ，任务调度 开启任务
        # 添加一个任务uid
        task_uid = greate_task_uid()
        collection_task = CollectionTask(task_uid=task_uid,
                                         datasource_id=data_source_db.id,
                                         task_status=DataSourceTaskStatusEnum.WAITING.value,
                                         total_count=0,
                                         records_count=0)
        db_session.add(collection_task)
        db_session.commit()
        # 开启任务
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
    搜索数据源

    Args:
        user_id (int): 用户ID
        session (Session): 数据库会话
        isadmin (bool): 是否为管理员
        page (int): 当前页码，默认为1
        per_page (int): 每页显示的数据量，默认为10

    Returns:
        Tuple[List[DataSource], int]: 第一个元素是搜索到的数据源列表，第二个元素是总记录数
    """
    # 构造基本查询
    query = session.query(DataSource)
    if not isadmin:
        query = query.filter(DataSource.owner_id == user_id)
    if name is not None:
        query = query.filter(DataSource.name.like(f"%{name}%"))
    if source_type is not None:
        query = query.filter(DataSource.source_type == source_type)
    # 计算总记录数
    total_count = query.count()
    # 执行分页查询
    data_sources = query.order_by(DataSource.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return data_sources, total_count


def update_data_source(db_session: Session, data_source_id: int, update_data: DataSourceUpdate):
    """
    更新数据源记录

    Args:
        db_session (Session): 数据库会话
        data_source_id (int): 要更新的数据源ID
        update_data (DataSourceUpdate): 更新数据

    Returns:
        Optional[DataSource]: 更新后的数据源对象，如果未找到则返回 None
    """

    # 根据ID查询数据源记录
    data_source = db_session.query(DataSource).get(data_source_id)
    if data_source is None:
        return None

    # 更新非空字段
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
    # 提交更改到数据库
    db_session.commit()

    return data_source


def delete_data_source(db_session: Session, data_source_id: int):
    """
    删除数据源记录
    Args:
        db_session (Session): 数据库会话
        data_source_id (int): 要删除的数据源ID
    Returns:
        bool: 删除操作是否成功
    """
    # 删除任务
    db_session.query(CollectionTask).filter_by(datasource_id=data_source_id).delete()
    # # 根据ID查询数据源记录然后删除
    data_source = db_session.query(DataSource).get(data_source_id)
    if data_source is None:
        return False
    # 删除数据源记录
    db_session.delete(data_source)
    db_session.commit()
    return True


# 数据源相关
def get_datasource(db_session: Session, datasource_id: int):
    """
    获取数据源信息
    Args:
        db_session (Session): 数据库会话
        datasource_id (int): 数据源ID
    Returns:
        DataSource: 数据源对象
    """
    data_source = db_session.query(DataSource).get(datasource_id)
    return data_source


def has_execting_tasks(db_session: Session, datasource_id: int):
    """
    检查数据源是否有正在执行的任务
    Args:
        db_session (Session): 数据库会话
        datasource_id (int): 数据源ID
    Returns:
        bool: 是否有正在执行的任务
    """
    query = db_session.query(CollectionTask).filter_by(datasource_id=datasource_id,
                                                       task_status=DataSourceTaskStatusEnum.EXECUTING.value).exists()
    return db_session.query(query).scalar()


def get_collection_task(db_session: Session, task_id: int):
    """
    获取采集任务信息
    Args:
        db_session (Session): 数据库会话
        task_id (int): 任务ID
    Returns:
        CollectionTask: 采集任务对象
    """
    collection_task = db_session.query(CollectionTask).get(task_id)
    return collection_task


def get_collection_task_by_uid(db_session: Session, task_uid: str):
    """
    根据任务UID获取唯一的采集任务信息

    Args:
        db_session (Session): 数据库会话
        task_uid (str): 任务UID

    Returns:
        CollectionTask: 唯一的采集任务对象，如果不存在则返回 None
    """
    # 假设 CollectionTask 模型中有一个唯一的 task_uid 字段
    collection_task = db_session.query(CollectionTask).filter(CollectionTask.task_uid == task_uid).one_or_none()
    return collection_task


def search_collection_task(
        datasource_id: int,
        session: Session,
        page: int = 1,
        per_page: int = 10
) -> Tuple[List[CollectionTask], int]:
    """
    搜索数据源下的任务列表
    Args:
        datasource_id (int): 数据源id
        session (Session): 数据库会话
        page (int): 当前页码，默认为1
        per_page (int): 每页显示的数据量，默认为10

    Returns:
        Tuple[List[CollectionTask], int]: 第一个元素是搜索到的数据源任务列表，第二个元素是总记录数
    """
    # 构造基本查询
    query = session.query(CollectionTask).filter_by(datasource_id=datasource_id)
    # 计算总记录数
    total_count = query.count()
    # 执行分页查询
    collection_tasks = query.order_by(CollectionTask.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return collection_tasks, total_count


def search_collection_task_all(
        datasource_id: int,
        session: Session,
) -> Tuple[List[CollectionTask], int]:
    """
    搜索数据源下的任务列表
    Args:
        datasource_id (int): 数据源id
        session (Session): 数据库会话
    Returns:
        Tuple[List[CollectionTask], int]: 第一个元素是搜索到的数据源任务列表，第二个元素是总记录数
    """
    # 构造基本查询
    query = session.query(CollectionTask).filter_by(datasource_id=datasource_id)
    # 计算总记录数
    total_count = query.count()
    # 执行分页查询
    collection_tasks = query.order_by(CollectionTask.created_at).all()
    return collection_tasks, total_count


def execute_collection_task(db_session: Session, collection_task: CollectionTask, user_name: str, user_token: str):
    """
    执行任务
    Args:
        db_session (Session): 数据库会话
        collection_task (CollectionTask): 任务对象
        user_name (str): 用户名称
        user_token (str): 用户token
    Returns:
        bool: 执行操作是否成功
    """
    try:
        if not collection_task.datasource:
            return False, "数据源不存在"
        task_celery_uid = run_celery_task(collection_task.datasource, collection_task.task_uid, user_name, user_token)
        if task_celery_uid is None:
            return False, "数据源类型错误"
        collection_task.task_celery_uid = task_celery_uid
        db_session.commit()
        return True, None
    except Exception as e:
        print(f"执行任务失败: {str(e)}")
        return False, str(e)


def stop_collection_task(db_session: Session, collection_task: CollectionTask):
    """
    执行任务
    Args:
        db_session (Session): 数据库会话
        collection_task (CollectionTask): 任务对象
    Returns:
        bool: 执行操作是否成功
    """
    try:
        if not collection_task.datasource:
            return False, "数据源不存在"
        result = stop_celery_task(collection_task.task_uid)
        if result:
            collection_task.task_status = DataSourceTaskStatusEnum.STOP.value
            db_session.commit()
        else:
            return False, "结束任务异常"
        return True, None
    except Exception as e:
        print(f"执行任务失败: {str(e)}")
        return False, str(e)


def execute_new_collection_task(db_session: Session, datasource: DataSource, user_name: str, user_token: str):
    """
    执行任务
    Args:
        db_session (Session): 数据库会话
        datasource (DataSource): 数据源ID
        user_name (str): 用户名称
        user_token (str): 用户token
    Returns:
        bool: 执行操作是否成功
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
            return False, "数据源类型错误"
        collection_task.task_celery_uid = task_celery_uid
        collection_task.task_status = DataSourceTaskStatusEnum.EXECUTING.value
        db_session.commit()
        return True, None
    except Exception as e:
        print(f"执行任务失败: {str(e)}")
        return False, str(e)


def read_task_log(collection_task: CollectionTask):
    """
    读取任务日志
    Args:
        collection_task (CollectionTask): 任务对象
    Returns:
        str: 任务日志
    """
    log_file_path = get_datasource_log_path(collection_task.task_uid)
    try:
        with open(log_file_path, 'r') as f:
            file_content = f.read()
        return True, file_content
    except Exception as e:
        print(f"查询日志失败: {str(e)}")
        return False, str(e)
