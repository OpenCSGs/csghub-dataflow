from data_server.schemas.responses import JobsResponse
from sqlalchemy import select
from data_server.database.session import get_sync_session
from sqlalchemy.orm import Session
from data_server.database.bean.work import Worker
from typing import Annotated, Union

from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import List, Optional
from data_server.logic.models import Recipe, Tool
from data_server.schemas import responses
from data_server.job.JobsManager import list_jobs, retreive_job, get_job_data, create_new_job, delete_job_by_id, search_job, retreive_log

router = APIRouter()


@router.get("/test", response_model=JobsResponse, description="Get job list")
async def job_test(session: Session = Depends(get_sync_session)):
    workers = session.query(Worker).all()
    res = JobsResponse(
        data=workers,
        total=len(workers),
    )
    return res


@router.get("", response_model=List[responses.ShowJob], description="Get job list by current_user, provide query params to search the job name by string")
async def job_list(
        query: Optional[str] = None,
        user_id: Annotated[str | None, Header(alias="user_id")] = None,
        isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
        session: Session = Depends(get_sync_session)):
    try:
        if query:
            jobs = search_job(query, user_id, session, isadmin)
        else:
            jobs = list_jobs(user_id, session, isadmin)
        return jobs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


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


@router.get("/log/{id}", description="Get the log of the job by id")
async def read_log(id: int,
                   user_id: Annotated[str | None,
                                      Header(alias="user_id")] = None,
                   isadmin: Annotated[bool | None,
                                      Header(alias="isadmin")] = None,
                   session: Session = Depends(get_sync_session)):
    try:
        log = retreive_log(job_id=id, user_id=user_id,
                           session=session, isadmin=isadmin, )
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


@router.post("", response_model=responses.JobCreate, description="Create the dataflow job")
def create_job(
    config:  Union[Recipe, Tool],
    user_id: Annotated[str | None, Header(alias="user_id")] = None,
    user_name: Annotated[str | None, Header(alias="user_name")] = None,
    user_token: Annotated[str | None, Header(alias="user_token")] = None,
):
    try:
        result = create_new_job(
            job_cfg=config, user_id=user_id, user_name=user_name, user_token=user_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


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
