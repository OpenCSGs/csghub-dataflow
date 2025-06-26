from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from data_server.database.bean.base import Base
import datetime


class Job(Base):
    __tablename__ = "job"

    job_id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, nullable=False)
    uuid = Column(String)
    job_source = Column(String)
    job_type = Column(String)
    status = Column(String)
    data_source = Column(String)
    data_target = Column(String)
    work_dir = Column(String)
    data_count = Column(Integer)
    process_count = Column(Integer)
    date_posted = Column(DateTime, default=datetime.datetime.now)
    date_finish = Column(DateTime)
    is_active = Column(Boolean(), default=True)
    owner_id = Column(Integer)
    repo_id = Column(String)
    branch = Column(String)
    export_repo_id = Column(String)
    export_branch_name = Column(String)
    first_op = Column(String)
