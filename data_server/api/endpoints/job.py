from data_server.logic.config import build_templates_with_filepath
import yaml
from data_server.algo_templates.utils.parse_algo_dslText import convert_raw_to_processed
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Annotated, Union, List, Optional
from fastapi import APIRouter, HTTPException, status, Header, Depends, Query, Body

from data_server.database.session import get_sync_session
from data_server.database.bean.work import Worker
from data_server.logic.models import Recipe, Tool,OperatorIdentifier
from data_server.schemas import responses
from data_server.schemas.responses import (
    JobsResponse, JobListResponse, JOB_STATUS,
    response_success, response_fail
)
from data_server.datasource.DatasourceManager import apply_cluster_resource_fields
from data_server.job.JobsManager import (
    list_jobs, retreive_job, get_job_data, create_new_job, delete_job_by_id,
    search_job, retreive_log, parse_yaml_config, create_pipline_new_job, stop_pipline_task,
    execute_job, enrich_job_for_list, build_job_log_context,
)
from data_server.utils.task_access import (
    can_delete_task,
    resolve_organization_admin_uuids_for_delete,
    resolve_organization_namespace_uuids_for_list,
)
from data_server.utils.jwt_utils import parse_jwt_token
from data_server.job.JobModels import Job
from data_server.job.SubTaskManager import (
    get_pipline_job_operators_status_from_subtasks,
    get_pipline_job_total_operators_status_from_subtasks,
    get_subtask_for_parent,
)
from data_server.utils.csghub_task_logs import fetch_csghub_logs_payload
from data_server.log_tools.tools import get_pipline_job_log_List
from data_server.utils.csghub_namespace import parse_namespace_fields
from data_server.utils.csghub_status_sync import (
    should_query_csghub_status,
    sync_csghub_main_task_status_by_query,
)
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
        ).filter(Job.is_active.is_(True)).group_by(Job.status).all()
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
        job_source: Optional[str] = Query(None, description="pipeline 或 tool，筛选算子/工具任务"),
        namespace_uuid: Optional[str] = Query(
            None, description="管理员可选：按单个组织 namespace 缩小范围"
        ),
        user_id: Annotated[str | None, Header(alias="User-Id")] = None,
        user_name: Annotated[str | None, Header(alias="User-Name")] = None,
        user_token: Annotated[str | None, Header(alias="User-Token")] = None,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
        isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
        session: Session = Depends(get_sync_session)):
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        if query:
            jobs, total, total_pages = search_job(
                query, user_id, session, isadmin, page, page_size,
                organization_namespace_uuids=org_uuids,
                namespace_uuid=namespace_uuid,
                job_source=job_source,
            )
        else:
            jobs, total, total_pages = list_jobs(
                user_id, session, isadmin, page, page_size,
                organization_namespace_uuids=org_uuids,
                namespace_uuid=namespace_uuid,
                job_source=job_source,
            )

        return JobListResponse(
            data=[
                enrich_job_for_list(job, user_id=user_id, isadmin=isadmin)
                for job in jobs
            ],
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


@router.get("/log_context/{job_id}", description="获取任务 CSGHub 日志参数（非日志内容）")
async def job_log_context(
    job_id: int,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    session: Session = Depends(get_sync_session),
):
    try:
        job = get_job_data(
            job_id=job_id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
        )
        if not job:
            return response_fail(msg="job not exist")
        ctx = build_job_log_context(job)
        return response_success(data=ctx)
    except Exception as e:
        logger.error(f"job_log_context failed: {e}")
        return response_fail(msg="获取任务日志参数失败")
    finally:
        session.close()


@router.get("/{id}", description="Get job details; sync_status=true 时按条件向 CSGHub 拉取主/子任务状态（仅详情页使用）")
async def read_job(id: int,
                   user_id: Annotated[str | None,
                                      Header(alias="User-Id")] = None,
                   isadmin: Annotated[bool | None,
                                      Header(alias="isadmin")] = None,
                   namespace_uuid: Optional[str] = Query(None),
                   user_name: Annotated[str | None, Header(alias="User-Name")] = None,
                   user_token: Annotated[str | None, Header(alias="User-Token")] = None,
                   authorization: Annotated[str | None, Header(alias="Authorization")] = None,
                   sync_status: bool = False,
                   session: Session = Depends(get_sync_session)):
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        current_job = get_job_data(
            job_id=id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            organization_namespace_uuids=org_uuids,
            namespace_uuid=namespace_uuid,
        )
        if sync_status and current_job and should_query_csghub_status(current_job, "job"):
            sync_csghub_main_task_status_by_query(
                    session,
                    flow_id=current_job.flow_id,
                    csghub_job_id=current_job.csghub_job_id,
                    user_token=user_token,
                    authorization=authorization,
                csghub_response_payload=current_job.csghub_response_payload,
            )
            session.refresh(current_job)
        job = retreive_job(
            job_id=id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            organization_namespace_uuids=org_uuids,
            namespace_uuid=namespace_uuid,
        )
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with this id {id} does not exist",
            )
        job_record = job.get("job")
        if job_record is not None:
            owner_id = getattr(job_record, "owner_id", None)
            can_del = can_delete_task(
                owner_id=owner_id, user_id=user_id, isadmin=isadmin
            )
            if hasattr(job_record, "model_copy"):
                job["job"] = job_record.model_copy(update={"can_delete": can_del})
            else:
                setattr(job_record, "can_delete", can_del)
        return job
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()


@router.get("/log/{id}", description="Get the log of the job by id")
async def read_log(
    id: int,
    dag_task_id: str | None = None,
    stream: bool = False,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    session: Session = Depends(get_sync_session),
):
    """
    Pipeline / Tool task logs.
    Submitted to CSGHub: remote logs (no dag_task_id = full main task; with dag_task_id = subtask).
    Not submitted to CSGHub: fallback to local work_dir/log files (main task only).
    """
    try:
        job = get_job_data(
            job_id=id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
        )
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with this id {id} does not exist",
            )

        if job.csghub_job_id and job.job_source in ("pipeline", "tool", "datasource"):
            if dag_task_id:
                subtask = get_subtask_for_parent(
                    session,
                    parent_type=job.job_source or "pipeline",
                    parent_id=job.job_id,
                    dag_task_id=dag_task_id,
                )
                if subtask is None:
                    return response_fail(msg=f"子任务不存在: {dag_task_id}")
            try:
                data = fetch_csghub_logs_payload(
                    namespace_uuid=job.namespace_uuid,
                    csghub_job_id=job.csghub_job_id,
                    flow_id=job.flow_id,
                    csghub_response_payload=job.csghub_response_payload,
                    dag_task_id=dag_task_id,
                    stream=stream,
                    user_token=user_token,
                )
                return response_success(data=data)
            except ValueError as exc:
                return response_fail(msg=str(exc))
            except RuntimeError as exc:
                return response_fail(msg=str(exc))

        if dag_task_id:
            return response_fail(msg="任务未提交到 CSGHub，无法按子任务查询远端日志")

        log = retreive_log(job_id=id, user_id=user_id, session=session, isadmin=isadmin)
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job log not found for id {id}",
            )
        session_log = log.get("session_log") if isinstance(log, dict) else str(log)
        return response_success(
            data={
                "logs": session_log,
                "scope": "main",
                "source": "local",
                "dag_task_id": None,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        session.close()


@router.get("/pipline_job_log/{id}", response_model=dict,description="Get the log of the job by id")
async def read_pipline_job_log(id: int,
                               user_id: Annotated[str | None,Header(alias="User-Id")] = None,
                               isadmin: Annotated[bool | None,Header(alias="isadmin")] = None,
                               page: int = 1,
                               page_size: int = 20,
                               level: str = "",
                               ops_name: str =  "",
                               session: Session = Depends(get_sync_session)):
    try:
        job = get_job_data(job_id=id, user_id=user_id, session=session, isadmin=isadmin)
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
                               user_id: Annotated[str | None, Header(alias="User-Id")] = None,
                               user_name: Annotated[str | None, Header(alias="User-Name")] = None,
                               user_token: Annotated[str | None, Header(alias="User-Token")] = None,
                               authorization: Annotated[str | None, Header(alias="Authorization")] = None,
                               isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
                               session: Session = Depends(get_sync_session)):
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        job = get_job_data(
            job_id=operators.job_id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            organization_namespace_uuids=org_uuids,
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
        )
        if not job:
            return response_fail(msg="job not exist")
        status_list = get_pipline_job_operators_status_from_subtasks(
            session,
            parent_type=job.job_source or "pipeline",
            parent_id=job.job_id,
            job_uid=job.uuid or "",
            flow_id=job.flow_id,
            operators=operators.operators,
        )
        return response_success(data=status_list)
    except Exception as e:
        return response_fail(msg=f"failed by error :{e}")

@router.get("/get_pipline_job_operators_status/{job_id}", response_model=dict,description="Get the operators_status of the job by id")
async def get_pipline_job_operators_status_api(
    job_id: int,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    session: Session = Depends(get_sync_session),
):
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        job = get_job_data(
            job_id=job_id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            organization_namespace_uuids=org_uuids,
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
        )
        if not job:
            return response_fail(msg="job not exist")
        status_list = get_pipline_job_total_operators_status_from_subtasks(
            session,
            parent_type=job.job_source or "pipeline",
            parent_id=job.job_id,
            job_uid=job.uuid or "",
            flow_id=job.flow_id,
        )
        return response_success(data=status_list)
    except Exception as e:
        return response_fail(msg=f"failed by error :{e}")
    finally:
        session.close()


@router.get("/resource/{id}", response_model=dict,description="Get the process resource of the job by id")
async def read_task_resource_info(
    id: int,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    session: Session = Depends(get_sync_session),
):
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        job = get_job_data(
            job_id=id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            organization_namespace_uuids=org_uuids,
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
        )
        if not job:
            return response_fail(msg="job not exist")
        return response_fail(msg="任务资源监控旧链路已下线")
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

    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    owner_org_id: Annotated[str | None, Header(alias="Org-Id")] = None,
    owner_org_name: Annotated[str | None, Header(alias="Org-Name")] = None,
):
    # print(user_id)
    # print(user_name)
    # print(user_token)
    # print(config)
    if isinstance(config, Recipe):
        print("Matched Recipe class")
        # Handle Recipe logic (e.g., parse process field)
    elif isinstance(config, Tool):
        print("Matched Tool class")
    try:
        parse_namespace_fields(
            namespace_uuid=config.namespace_uuid,
            namespace_type=config.namespace_type,
        )
        result = create_new_job(
            job_cfg=config, user_id=user_id, user_name=user_name, user_token=user_token,
            owner_org_id=owner_org_id, owner_org_name=owner_org_name)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/pipeline", response_model=dict,description="Create the dataflow job")
def create_pipline_job(
    config:  Union[Recipe, Tool],
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    owner_org_id: Annotated[str | None, Header(alias="Org-Id")] = None,
    owner_org_name: Annotated[str | None, Header(alias="Org-Name")] = None,
):
    try:
        if config.job_source == "tool":
            return response_fail(msg="tool can't run pipline")

        yaml_config = parse_yaml_config(config.dslText,config)
        parse_namespace_fields(
            namespace_uuid=config.namespace_uuid,
            namespace_type=config.namespace_type,
        )
        result = create_pipline_new_job(
            job_cfg=config, user_id=user_id, user_name=user_name, user_token=user_token,
            yaml_config=yaml_config,
            owner_org_id=owner_org_id, owner_org_name=owner_org_name)
        return response_success(data=result)
    except Exception as e:
        logger.error(f"Failed to create pipline  job: {str(e)}")
        return response_fail(msg=f"Failed to create pipline  job: {str(e)}")


@router.post("/stop_pipline_job", response_model=dict, description="stop the dataflow job")
def stop_pipline_job(
    job_id: int,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    session: Session = Depends(get_sync_session),
):
    try:
        job = get_job_data(
            job_id=job_id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
        )
        if not job:
            return response_fail(msg="job not exist")
        if job.status == JOB_STATUS.PROCESSING.value or job.status == JOB_STATUS.QUEUED.value:
            result, msg = stop_pipline_task(session, job, user_token=user_token)
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
async def run_pipline_job(
    job_id: int,
    data: dict = Body(default={}),
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    execute_time: str | None = None,
    session: Session = Depends(get_sync_session),
):
    try:
        job = get_job_data(
            job_id=job_id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
        )
        if not job:
            return response_fail(msg="job not exist")

        apply_cluster_resource_fields(
            job,
            cluster_id=data.get("cluster_id"),
            cluster_name=data.get("cluster_name"),
            resource_id=data.get("resource_id"),
            resource_name=data.get("resource_name"),
            space_resource_id=data.get("space_resource_id"),
            storage_size=data.get("storage_size"),
        )
        session.commit()

        ok, msg = execute_job(
            job,
            user_id,
            user_name,
            user_token,
            session,
            data.get("namespace_uuid"),
            data.get("namespace_type"),
            execute_time,
        )
        if not ok:
            return response_fail(msg=msg or "任务执行失败")
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
                       Header(alias="User-Id")] = None,
    isadmin: Annotated[bool | None,
                       Header(alias="isadmin")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    namespace_uuid: Optional[str] = Query(None),
    session: Session = Depends(get_sync_session)
):
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        job = get_job_data(
            job_id=id,
            user_id=user_id,
            session=session,
            isadmin=isadmin,
            organization_namespace_uuids=org_uuids,
            namespace_uuid=namespace_uuid,
        )
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {id} does not exist",
            )
        if job.status == JOB_STATUS.PROCESSING.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The job has not been completed yet.",
            )
        if not can_delete_task(
            owner_id=job.owner_id,
            user_id=user_id,
            isadmin=isadmin,
            org_admin_uuids=resolve_organization_admin_uuids_for_delete(
                user_name=user_name,
                authorization=authorization,
                user_token=user_token,
                isadmin=isadmin,
            ),
            namespace_uuid=getattr(job, "namespace_uuid", None),
            namespace_type=getattr(job, "namespace_type", None),
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅任务创建者或管理员可删除",
            )
        delete_job_by_id(id=id, session=session)
        return {"detail": "Successfully deleted."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        session.close()
