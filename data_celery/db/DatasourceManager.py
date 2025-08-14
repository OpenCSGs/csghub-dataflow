from data_server.datasource.DatasourceModels import CollectionTask
from sqlalchemy.orm import Session


def get_collection_task_by_uid(db_session: Session, task_uid: str):

    collection_task = db_session.query(CollectionTask).filter(CollectionTask.task_uid == task_uid).one_or_none()
    return collection_task
