import json

from data_server.logic.config import build_templates_with_filepath
import yaml
from data_server.algo_templates.utils.parse_algo_dslText import convert_raw_to_processed
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Annotated, Union, List, Optional
from fastapi import APIRouter, HTTPException, status, Header, Depends, Query, Body

from data_server.database.session import get_sync_session, get_celery_worker_redis_db, get_celery_task_process_resource_key
from data_server.database.bean.work import Worker
from data_server.logic.models import Recipe, Tool,OperatorIdentifier
from data_server.schemas import responses
from data_server.schemas.responses import (
    JobsResponse, JobListResponse, JOB_STATUS,
    response_success, response_fail
)
from data_server.job.JobsManager import (
    list_jobs, retreive_job, get_job_data, create_new_job, delete_job_by_id,
    search_job, retreive_log, parse_yaml_config, create_pipline_new_job, stop_pipline_task,
    run_pipline_job_only
)
from data_server.utils.jwt_utils import parse_jwt_token
from data_server.job.JobModels import Job
from data_celery.mongo_tools.tools import get_pipline_job_log_List,get_pipline_job_operators_status,get_pipline_job_total_operators_status
from loguru import logger
router = APIRouter()


@router.get("/test", response_model=JobsResponse, description="Get job list")
async def job_test(session: Session = Depends(get_sync_session)):
    try:
        workers = session.query(Worker).all()
        res = JobsResponse(
            data=workers,
            total=len(workers),
        )
        return res
    finally:
        session.close()


@router.get("/get_task_statistics", response_model=dict)
async def get_task_statistics(db: Session = Depends(get_sync_session)):
    try:
        status_counts = db.query(
            Job.status,
            func.count(Job.job_id).label('count')
        ).group_by(Job.status).all()
        statistics = {}
        for status, count in status_counts:
            status_name = JOB_STATUS(status).name
            statistics[status_name] = count
        for status_enum in JOB_STATUS:
            if status_enum.name not in statistics:
                statistics[status_enum.name] = 0
        return response_success(data=statistics)
    finally:
        db.close()

@router.get("", response_model=JobListResponse, description="Get job list by current_user, provide query params to search the job name by string")
async def job_list(
        query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        user_id: Annotated[str | None, Header(alias="user_id")] = None,
        isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
        session: Session = Depends(get_sync_session)):
    try:
        if query:
            jobs, total, total_pages = search_job(query, user_id, session, isadmin, page, page_size)
        else:
            jobs, total, total_pages = list_jobs(user_id, session, isadmin, page, page_size)

        return JobListResponse(
            data=jobs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@router.get("/{id}", description="Get the details of the job by id")
async def read_job(id: int,
                   user_id: Annotated[str | None,
                                      Header(alias="user_id")] = None,
                   isadmin: Annotated[bool | None,
                                      Header(alias="isadmin")] = None,
                   session: Session = Depends(get_sync_session)):
    try:
        job = retreive_job(job_id=id, user_id=user_id,
                           session=session, isadmin=isadmin)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with this id {id} does not exist",
            )
        return job
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@router.get("/log/{id}", description="Get the log of the job by id")
async def read_log(id: int,
                   user_id: Annotated[str | None,
                                      Header(alias="user_id")] = None,
                   isadmin: Annotated[bool | None,
                                      Header(alias="isadmin")] = None,
                   session: Session = Depends(get_sync_session)):
    try:
        log = retreive_log(job_id=id, user_id=user_id,
                           session=session, isadmin=isadmin )
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with this id {id} does not exist",
            )
        return log
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@router.get("/pipline_job_log/{id}", response_model=dict,description="Get the log of the job by id")
async def read_pipline_job_log(id: int,
                               user_id: Annotated[str | None,Header(alias="user_id")] = None,
                               page: int = 1,
                               page_size: int = 20,
                               level: str = "",
                               ops_name: str =  "",
                               session: Session = Depends(get_sync_session)):
    try:
        job = get_job_data(job_id=id, user_id=user_id, session=session)
        if not job:
            return response_fail(msg="job not exist")
        log_list = get_pipline_job_log_List(task_uid=job.uuid, page=page, page_size=page_size, level=level, ops_name=ops_name)
        return response_success(data=log_list)
    except Exception as e:
        return response_fail(msg=f"failed by error :{e}")
    finally:
        session.close()


@router.post("/pipline_job_operators_status", response_model=dict,description="Get the operators_status of the job by id")
async def read_pipline_job_operators_status(
                               operators: OperatorIdentifier,
                               user_id: Annotated[str | None,Header(alias="user_id")] = None,
                               session: Session = Depends(get_sync_session)):
    try:
        job = get_job_data(job_id=operators.job_id, user_id=user_id, session=session)
        if not job:
            return response_fail(msg="job not exist")
        status_list = get_pipline_job_operators_status(job_uid=job.uuid, operators=operators.operators)
        return response_success(data=status_list)
    except Exception as e:
        return response_fail(msg=f"failed by error :{e}")

@router.get("/get_pipline_job_operators_status/{job_id}", response_model=dict,description="Get the operators_status of the job by id")
async def get_pipline_job_operators_status_api(job_id: int,
                               user_id: Annotated[str | None,Header(alias="user_id")] = None,
                               session: Session = Depends(get_sync_session)):
    try:
        job = get_job_data(job_id=job_id, user_id=user_id, session=session)
        if not job:
            return response_fail(msg="job not exist")
        status_list = get_pipline_job_total_operators_status(job_uid=job.uuid)
        return response_success(data=status_list)
    except Exception as e:
        return response_fail(msg=f"failed by error :{e}")
    finally:
        session.close()


@router.get("/resource/{id}", response_model=dict,description="Get the process resource of the job by id")
async def read_task_resource_info(id: int,
                    user_id: Annotated[str | None,
                    Header(alias="user_id")] = None,
                    session: Session = Depends(get_sync_session)):
    try:
        job = get_job_data(job_id=id, user_id=user_id,session=session)
        if not job:
            return response_fail(msg="job not exist")
        # red job task process resource info
        process_resource_key = get_celery_task_process_resource_key(job.uuid)
        redis_celery = get_celery_worker_redis_db()
        process_resources = redis_celery.get(process_resource_key)
        if process_resources and len(process_resources) > 0:
            task_resource_info = json.loads(process_resources)
            return response_success(data=task_resource_info)
        return response_fail(msg="no process resource info found")
    except Exception as e:
        return response_fail(msg=f"failed by error :{e}")
    finally:
        session.close()


@router.post("", response_model=responses.JobCreate, description="Create the dataflow job")
def create_job(

    config:  Union[Tool],

    # config:  Union[Recipe, Tool],
    # config:  Union[Tool,Recipe],
    # config: Union[Tool],

    user_id: Annotated[str | None, Header(alias="user_id")] = None,
    user_name: Annotated[str | None, Header(alias="user_name")] = None,
    user_token: Annotated[str | None, Header(alias="user_token")] = None
):
    # print(user_id)
    # print(user_name)
    # print(user_token)
    # print(config)
    if isinstance(config, Recipe):
        print("匹配到 Recipe 类")
        # 处理 Recipe 逻辑（如解析 process 字段）
    elif isinstance(config, Tool):
        print("匹配到 Tool 类")
    try:
        result = create_new_job(
            job_cfg=config, user_id=user_id, user_name=user_name, user_token=user_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/pipeline", response_model=dict,description="Create the dataflow job")
def create_pipline_job(
    config:  Union[Recipe, Tool],
    user_id: Annotated[str | None, Header(alias="user_id")] = None,
    user_name: Annotated[str | None, Header(alias="user_name")] = None,
    user_token: Annotated[str | None, Header(alias="user_token")] = None
):
    try:
        if config.job_source == "tool":
            return response_fail(msg="tool can't run pipline")

        yaml_config = parse_yaml_config(config.dslText,config)
        result = create_pipline_new_job(
            job_cfg=config, user_id=user_id, user_name=user_name, user_token=user_token,yaml_config=yaml_config)
        return response_success(data=result)
    except Exception as e:
        logger.error(f"Failed to create pipline  job: {str(e)}")
        return response_fail(msg=f"Failed to create pipline  job: {str(e)}")


@router.post("/stop_pipline_job", response_model=dict, description="stop the dataflow job")
def stop_pipline_job(job_id: int,
                     user_id: Annotated[str | None, Header(alias="user_id")] = None,
                     session: Session = Depends(get_sync_session)):
    try:
        job = get_job_data(job_id=job_id, user_id=user_id, session=session)
        if not job:
            return response_fail(msg="job not exist")
        if job.task_run_host is None or len(job.task_run_host) == 0:
            return response_fail(msg="job host not set")
        if job.job_celery_work_name is None or len(job.job_celery_work_name) == 0:
            return response_fail(msg="job work name not set")
        if job.status == JOB_STATUS.PROCESSING.value or job.status == JOB_STATUS.QUEUED.value:
            result, msg = stop_pipline_task(session,job)
            if result:
                return response_success(data="Task stopped successfully or queued")
            return response_fail(msg=msg)
        else:
            return response_fail(msg="job not processing")
    except Exception as e:
        logger.error(f"Failed to stop pipline  job: {str(e)}")
        return response_fail(msg=f"Failed to stop pipline  job: {str(e)}")
    finally:
        session.close()



@router.post("/job/execute/{job_id}", response_model=dict)
async def run_pipline_job(job_id: int,
                    user_id: Annotated[str | None, Header(alias="user_id")] = None,
                    user_name: Annotated[str | None, Header(alias="user_name")] = None,
                    user_token: Annotated[str | None, Header(alias="user_token")] = None,
                    execute_time: str | None = None,
                    session: Session = Depends(get_sync_session)
                   ):
    try:
        job = get_job_data(job_id=job_id, user_id=user_id, session=session)
        if not job:
            return response_fail(msg="job not exist")

        run_pipline_job_only(job, user_id, user_name, user_token,session,execute_time)
        return response_success(data="job run successfully")
    except Exception as e:
        logger.error(f"Failed to run pipline job: {str(e)}")
        return response_fail(msg=f"Failed to run pipline job: {str(e)}")
    finally:
        session.close()



@router.delete("/{id}", description="Delete the Job by id")
def delete_job(
    id: int,
    user_id: Annotated[str | None,
                       Header(alias="user_id")] = None,
    isadmin: Annotated[bool | None,
                       Header(alias="isadmin")] = None,
    session: Session = Depends(get_sync_session)
):
    try:
        job = get_job_data(job_id=id, user_id=user_id,
                           session=session, isadmin=isadmin)
        if not job:
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {id} does not exist",
            )
        if job.status == JOB_STATUS.PROCESSING.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The job has not been completed yet.",
            )
        # delete anyway if user_id is supersuper?
        if str(job.owner_id) == str(user_id) or isadmin:
            delete_job_by_id(id=id, session=session)
            return {"detail": "Successfully deleted."}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not permitted!!!!"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()
