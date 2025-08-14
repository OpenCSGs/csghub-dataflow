from sqlalchemy.orm import Session
from data_server.formatify.FormatifyModels import DataFormatTask, DataFormatTaskStatusEnum

def get_formatify_task(db_session: Session, formatify_id: int):

    formatify_task = db_session.query(DataFormatTask).get(formatify_id)
    return formatify_task
