from sqlalchemy.orm import Session
from data_server.formatify.FormatifyModels import DataFormatTask, DataFormatTaskStatusEnum
# 数据源相关
def get_formatify_task(db_session: Session, formatify_id: int):
    """
    获取格式转换任务信息
    Args:
        db_session (Session): 数据库会话
        formatify_id (int): 格式化任务ID
    Returns:
        DataFormatTask: 格式化任务对象
    """
    formatify_task = db_session.query(DataFormatTask).get(formatify_id)
    return formatify_task
