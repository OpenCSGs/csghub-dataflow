from data_server.job.JobModels import Job
from data_server.schemas import responses
from sqlalchemy.orm import Session
from datetime import datetime
import os
import shutil
import re


def get_pipline_job_by_uid(db_session: Session, job_uid: str):
    """
    根据任务UID获取唯一的pipline任务信息

    Args:
        db_session (Session): 数据库会话
        job_uid (str): pipline任务UID

    Returns:
        Job: 唯一的pipline任务对象，如果不存在则返回 None
    """
    # 假设 Job 模型中有一个唯一的 task_uid 字段
    job = db_session.query(Job).filter(Job.uuid == job_uid).one_or_none()
    return job
