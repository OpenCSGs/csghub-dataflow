from data_server.job.JobModels import Job
from data_server.schemas import responses
from sqlalchemy.orm import Session
from datetime import datetime
import os
import shutil
import re


def get_pipline_job_by_uid(db_session: Session, job_uid: str):

    job = db_session.query(Job).filter(Job.uuid == job_uid).one_or_none()
    return job
