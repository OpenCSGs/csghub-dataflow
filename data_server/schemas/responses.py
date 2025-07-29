from typing import Any
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum
from typing import List


class ShowWorker(BaseModel):
    worker_uuid: str
    user_id: int
    worker_name: str
    class Config:
        from_attributes = True


class JobsResponse(BaseModel):
    total: int = 0
    data: List[ShowWorker]
    class Config:
        from_attributes = True


class JOB_STATUS(Enum):
    QUEUED = "Queued"
    PROCESSING = "Processing"
    FINISHED = "Finished"
    FAILED = "Failed"
    TIMEOUT = "Timeout"

# shared properties
class JobBase(BaseModel):
    job_id: int
    job_name: str


# this will be used to validate data while creating a Job
class JobCreate(JobBase):
    status: Optional[JOB_STATUS] = JOB_STATUS.QUEUED


# this will be used to format the response to not to have id,owner_id etc
class ShowJob(JobBase):
    job_source: Optional[str] = None
    job_type: Optional[str] = None
    data_source: Optional[str] = None
    data_target: Optional[str] = None
    date_posted: datetime
    status: str
    repo_id: Optional[str] = None
    branch: Optional[str] = None
    export_repo_id: Optional[str] = None
    export_branch_name: Optional[str] = None
    yaml_config: Optional[str] = None
    dslText: Optional[str] = None
    class Config:
        from_attributes = True  # to convert non dict obj to json
        extra = "allow"

class JobDetails(ShowJob):
    work_dir: str
    data_count: int
    process_count: int
    date_finish: datetime
    owner_id: int
    is_active: bool
    class Config:
        from_attributes = True  # to convert non dict obj to json
        extra = "allow"


def response_fail(msg: str = ""):
    res = {
        'msg': msg,
        'code': 500,
    }
    return res


def response_fail401(msg: str = ""):
    res = {
        'msg': msg,
        'code': 401,
    }
    return res

def response_success(data: Any = None, msg: str = ""):
    res = {
        'msg': msg,
        'code': 200,
        'data': data,
    }
    return res