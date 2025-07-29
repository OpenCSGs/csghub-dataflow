from data_server.datasource.DatasourceModels import CollectionTask
from sqlalchemy.orm import Session


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
