from datetime import datetime

from sqlalchemy.orm import Session
from data_server.formatify.FormatifyModels import DataFormatTask, DataFormatTaskStatusEnum
from data_server.formatify.schemas import DataFormatTaskRequest
import uuid, os
from typing import List, Tuple, Optional
import json
from data_server.job.SubTaskManager import clear_subtasks_for_parent, replace_subtasks_for_parent
from data_server.utils.csghub_dag_builder import build_formatify_dag
from data_server.utils.csghub_client import (
    build_csghub_payload,
    build_job_flow_id,
    collect_repo_ids,
    ensure_csghub_job_create_success,
    submit_job_to_csghub,
    try_cancel_csghub_job,
    resolve_csghub_remote_job_id,
)
from data_server.utils.csghub_namespace import parse_namespace_fields
from data_server.datasource.DatasourceManager import apply_cluster_resource_fields
from data_server.utils.csghub_namespace import NAMESPACE_TYPE_ORGANIZATION
from data_server.utils.task_access import (
    apply_task_list_scope,
    attach_can_delete,
    can_delete_task,
    log_task_list_sql,
    resolve_organization_namespace_uuids_for_list,
    soft_delete_record,
    user_can_access_task,
)
from loguru import logger


def _mark_formatify_task_failed(
    formatify_task: DataFormatTask,
    error: Exception | str | None = None,
    db_session: Session | None = None,
):
    now = datetime.now()
    formatify_task.task_status = DataFormatTaskStatusEnum.ERROR.value
    formatify_task.end_run_at = now
    formatify_task.csghub_status = "Failed"
    if db_session is not None and formatify_task.id:
        clear_subtasks_for_parent(
            db_session,
            parent_type="formatify",
            parent_id=formatify_task.id,
        )
    if error is not None:
        logger.error("Formatify task CSGHub submit failed: {}", error)


def greate_task_uid():

    return str(uuid.uuid4())


def _submit_formatify_task_to_csghub(
    db_session: Session,
    formatify_task: DataFormatTask,
    user_token: str | None,
    namespace: str,
    user_name: str | None = None,
    authorization: str | None = None,
    task_run_time: str | None = None,
):
    flow_id = build_job_flow_id("formatify", formatify_task.id)
    formatify_task.flow_id = flow_id
    task_params = formatify_task.to_dict()
    task_params["formatify_id"] = formatify_task.id
    task_params["user_name"] = user_name
    task_params["user_token"] = user_token
    task_params["authorization"] = authorization
    task_params["flow_id"] = flow_id
    if task_run_time:
        task_params["execute_time"] = task_run_time
    dag_tasks = build_formatify_dag(flow_id, task_params)
    payload = build_csghub_payload(
        job_id=flow_id,
        job_name=formatify_task.name,
        job_desc=formatify_task.des or formatify_task.name,
        resource_id=formatify_task.resource_id,
        resource_name=formatify_task.resource_name,
        storage_size=getattr(formatify_task, "storage_size", None),
        repo_ids=collect_repo_ids(
            formatify_task.to_csg_hub_repo_id,
            formatify_task.from_csg_hub_repo_id,
        ),
        dag_tasks=dag_tasks,
    )
    formatify_task.csghub_request_payload = json.dumps(payload, ensure_ascii=False)
    response = submit_job_to_csghub(
        payload, namespace=namespace, user_token=user_token, authorization=authorization
    )
    formatify_task.csghub_response_payload = json.dumps(response, ensure_ascii=False)
    parsed = ensure_csghub_job_create_success(response)
    formatify_task.csghub_job_id = parsed["job_id"]
    formatify_task.csghub_status = parsed.get("status") or "Submitted"
    replace_subtasks_for_parent(
        session=db_session,
        parent_type="formatify",
        parent_id=formatify_task.id,
        flow_id=flow_id,
        dag_tasks=dag_tasks,
    )
    return response


def create_formatify_task(
    db_session: Session,
    dataFormatTask: DataFormatTaskRequest,
    user_id,
    user_name: str,
    user_token: str,
    owner_org_id: str | None = None,
    owner_org_name: str | None = None,
    authorization: str | None = None,
):

    # create db model
    task_uid = greate_task_uid()
    nu, nt = parse_namespace_fields(
        namespace_uuid=dataFormatTask.namespace_uuid,
        namespace_type=dataFormatTask.namespace_type,
    )
    # Prepare skip_meta value (use provided value or default to False)
    skip_meta_value = dataFormatTask.skip_meta if dataFormatTask.skip_meta is not None else False
    
    data_format_task_db = DataFormatTask(name=dataFormatTask.name,
                                         des=dataFormatTask.des,
                                         from_csg_hub_dataset_name=dataFormatTask.from_csg_hub_dataset_name,
                                         from_csg_hub_dataset_id=dataFormatTask.from_csg_hub_dataset_id,
                                         from_csg_hub_dataset_branch=dataFormatTask.from_csg_hub_dataset_branch,
                                         from_data_type=dataFormatTask.from_data_type,
                                         from_csg_hub_repo_id=dataFormatTask.from_csg_hub_repo_id,
                                         to_csg_hub_dataset_name=dataFormatTask.to_csg_hub_dataset_name,
                                         to_csg_hub_dataset_id=dataFormatTask.to_csg_hub_dataset_id,
                                         to_csg_hub_dataset_default_branch=dataFormatTask.to_csg_hub_dataset_default_branch,
                                         to_csg_hub_repo_id=dataFormatTask.to_csg_hub_repo_id,
                                         to_data_type=dataFormatTask.to_data_type,
                                         mineru_api_url=dataFormatTask.mineru_api_url,
                                         mineru_backend=dataFormatTask.mineru_backend,
                                         skip_meta=skip_meta_value,
                                         cluster_id=dataFormatTask.cluster_id,
                                         cluster_name=dataFormatTask.cluster_name,
                                         resource_id=dataFormatTask.resource_id,
                                         resource_name=dataFormatTask.resource_name,
                                         storage_size=dataFormatTask.storage_size,
                                         task_uid=task_uid,
                                         task_status=DataFormatTaskStatusEnum.WAITING.value,
                                         owner_id=user_id,
                                         owner_org_id=owner_org_id,
                                         owner_org_name=owner_org_name,
                                         namespace_uuid=nu,
                                         namespace_type=nt)
    
    logger.info(f"Created task with skip_meta={skip_meta_value} for task {task_uid}")

    db_session.add(data_format_task_db)
    db_session.commit()
    try:
        _submit_formatify_task_to_csghub(
            db_session,
            data_format_task_db,
            user_token,
            nu,
            user_name=user_name,
            authorization=authorization,
        )
        data_format_task_db.task_status = DataFormatTaskStatusEnum.WAITING.value
    except Exception as e:
        _mark_formatify_task_failed(data_format_task_db, e, db_session)
        db_session.commit()
        raise
    db_session.commit()
    return data_format_task_db.id


def enrich_formatify_task_dict(
    task: DataFormatTask,
    *,
    user_id=None,
    isadmin: bool = False,
) -> dict:
    """List/detail view: fill CSGHub job_id, cloud resource names, etc."""
    data = task.to_dict()
    attach_can_delete(data, owner_id=task.owner_id, user_id=user_id, isadmin=isadmin)
    if task.csghub_job_id:
        data["csghub_remote_job_id"] = resolve_csghub_remote_job_id(
            task.csghub_job_id,
            flow_id=task.flow_id,
            csghub_response_payload=task.csghub_response_payload,
        )
    if data.get("resource_name") or not task.csghub_request_payload:
        return data
    try:
        payload = json.loads(task.csghub_request_payload)
    except Exception:
        return data
    if isinstance(payload, dict) and payload.get("resource_name"):
        data["resource_name"] = payload["resource_name"]
    return data


def get_formatify_task_by_uid(db_session: Session, task_uid: str):
    return db_session.query(DataFormatTask).filter_by(task_uid=task_uid).first()


def search_formatify_task(
        user_id,
        session: Session,
        isadmin: bool = False,
        query_dict=None,
        page: int = 1,
        per_page: int = 10,
        organization_namespace_uuids: list[str] | None = None,
        namespace_uuid: str | None = None,
) -> Tuple[List[DataFormatTask], int]:
    query = session.query(DataFormatTask)
    query = apply_task_list_scope(
        query,
        DataFormatTask,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
    )
    if query_dict:
        if query_dict['name']:
            query = query.filter(DataFormatTask.name.like(f"%{query_dict['name']}%"))

    log_task_list_sql(
        query,
        label="formatify",
        session=session,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
        page=page,
        per_page=per_page,
        name_filter=(query_dict or {}).get("name"),
    )
    total_count = query.count()

    data_format_tasks = (
        query.order_by(DataFormatTask.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return data_format_tasks, total_count


def update_formatify_task(db_session: Session, formatify_id: int, dataFormatTaskRequest: DataFormatTaskRequest):

    formatify_task: DataFormatTask = db_session.query(DataFormatTask).get(formatify_id)
    if formatify_task is None:
        return None
    updatable_fields = {
        'name', 'des', 'from_csg_hub_dataset_name', 'from_csg_hub_dataset_id',
        'from_csg_hub_dataset_branch', 'from_data_type', 'to_csg_hub_dataset_name',
        'to_csg_hub_dataset_id', 'to_csg_hub_dataset_default_branch', 'to_data_type',
        'mineru_api_url', 'mineru_backend'  # 'skip_meta' temporarily removed
    }
    for field in updatable_fields:
        value = getattr(dataFormatTaskRequest, field, None)
        if value is not None and value != '':
            setattr(formatify_task, field, value)

    db_session.commit()
    return formatify_task.to_dict()



def get_formatify_task_for_user(
    db_session: Session,
    formatify_id: int,
    user_id,
    isadmin: bool = False,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
    user_name: str | None = None,
    authorization: str | None = None,
    user_token: str | None = None,
) -> DataFormatTask | None:
    if organization_namespace_uuids is None and not isadmin:
        organization_namespace_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
    task = (
        db_session.query(DataFormatTask)
        .filter(DataFormatTask.id == formatify_id, DataFormatTask.is_active.is_(True))
        .first()
    )
    if not task:
        return None
    if user_can_access_task(
        task,
        user_id,
        isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
    ):
        return task
    return None


def delete_formatify_task(db_session: Session, formatify_id: int) -> bool:
    formatify_task = (
        db_session.query(DataFormatTask)
        .filter(DataFormatTask.id == formatify_id, DataFormatTask.is_active.is_(True))
        .first()
    )
    if formatify_task is None:
        return False
    if formatify_task.task_status == DataFormatTaskStatusEnum.EXECUTING.value:
        raise ValueError("任务执行中，无法删除")
    soft_delete_record(db_session, formatify_task)
    return True



def get_formatify_task(db_session: Session, formatify_id: int):
    return (
        db_session.query(DataFormatTask)
        .filter(DataFormatTask.id == formatify_id, DataFormatTask.is_active.is_(True))
        .first()
    )


def _copy_formatify_task(source: DataFormatTask) -> DataFormatTask:
    """Copy a new record from existing task (without CSGHub runtime fields)."""
    task_uid = greate_task_uid()
    return DataFormatTask(
        name=source.name,
        des=source.des,
        from_csg_hub_dataset_name=source.from_csg_hub_dataset_name,
        from_csg_hub_dataset_id=source.from_csg_hub_dataset_id,
        from_csg_hub_repo_id=source.from_csg_hub_repo_id,
        from_csg_hub_dataset_branch=source.from_csg_hub_dataset_branch,
        from_data_type=source.from_data_type,
        to_csg_hub_dataset_name=source.to_csg_hub_dataset_name,
        to_csg_hub_dataset_id=source.to_csg_hub_dataset_id,
        to_csg_hub_repo_id=source.to_csg_hub_repo_id,
        to_csg_hub_dataset_default_branch=source.to_csg_hub_dataset_default_branch,
        to_data_type=source.to_data_type,
        mineru_api_url=source.mineru_api_url,
        mineru_backend=source.mineru_backend,
        skip_meta=getattr(source, "skip_meta", False),
        cluster_id=source.cluster_id,
        cluster_name=source.cluster_name,
        resource_id=source.resource_id,
        resource_name=source.resource_name,
        storage_size=getattr(source, "storage_size", None),
        task_uid=task_uid,
        task_status=DataFormatTaskStatusEnum.WAITING.value,
        owner_id=source.owner_id,
        owner_org_id=source.owner_org_id,
        owner_org_name=source.owner_org_name,
        namespace_uuid=source.namespace_uuid,
        namespace_type=source.namespace_type,
    )


def execute_formatify_task(
    db_session: Session,
    formatify_task: DataFormatTask,
    user_name: str,
    user_token: str,
    authorization: str | None = None,
    task_run_time: str | None = None,
):
    """Waiting and not yet submitted to CSGHub: first submit this record."""
    try:
        nu, nt = parse_namespace_fields(
            namespace_uuid=formatify_task.namespace_uuid,
            namespace_type=formatify_task.namespace_type,
        )
        formatify_task.namespace_uuid = nu
        formatify_task.namespace_type = nt
        _submit_formatify_task_to_csghub(
            db_session,
            formatify_task,
            user_token,
            nu,
            user_name=user_name,
            authorization=authorization,
            task_run_time=task_run_time,
        )
        formatify_task.task_status = DataFormatTaskStatusEnum.WAITING.value
        db_session.commit()
        return True, None
    except Exception as e:
        _mark_formatify_task_failed(formatify_task, e, db_session)
        db_session.commit()
        logger.error(f"Formatify task execution failed: {e}")
        return False, str(e)


def execute_new_formatify_task(
    db_session: Session,
    source_task: DataFormatTask,
    user_name: str,
    user_token: str,
    authorization: str | None = None,
    task_run_time: str | None = None,
):
    """List "Execute": copy new task and submit to CSGHub; do not re-run old record."""
    try:
        nu, nt = parse_namespace_fields(
            namespace_uuid=source_task.namespace_uuid,
            namespace_type=source_task.namespace_type,
        )
        new_task = _copy_formatify_task(source_task)
        new_task.namespace_uuid = nu
        new_task.namespace_type = nt
        db_session.add(new_task)
        db_session.commit()
        try:
            _submit_formatify_task_to_csghub(
                db_session,
                new_task,
                user_token,
                nu,
                user_name=user_name,
                authorization=authorization,
                task_run_time=task_run_time,
            )
            new_task.task_status = DataFormatTaskStatusEnum.WAITING.value
            db_session.commit()
            return True, None
        except Exception as submit_err:
            _mark_formatify_task_failed(new_task, submit_err, db_session)
            db_session.commit()
            return False, str(submit_err)
    except Exception as e:
        logger.error(f"Formatify new task execution failed: {e}")
        return False, str(e)


def stop_formatify_task(
    db_session: Session,
    formatify_task: DataFormatTask,
    authorization: str | None = None,
):
    """Cancel format conversion task: CSGHub DELETE first, then mark canceled locally."""
    resolved_job_id = resolve_csghub_remote_job_id(
        formatify_task.csghub_job_id,
        flow_id=formatify_task.flow_id,
        csghub_response_payload=formatify_task.csghub_response_payload,
    )
    if resolved_job_id:
        formatify_task.csghub_job_id = resolved_job_id
    remote_ok, remote_err = try_cancel_csghub_job(
        namespace_uuid=formatify_task.namespace_uuid,
        csghub_job_id=formatify_task.csghub_job_id,
        authorization=authorization,
        flow_id=formatify_task.flow_id,
        csghub_response_payload=formatify_task.csghub_response_payload,
    )
    now = datetime.now()
    formatify_task.task_status = DataFormatTaskStatusEnum.STOP.value
    if formatify_task.end_run_at is None:
        formatify_task.end_run_at = now
    formatify_task.csghub_status = "Canceled"
    db_session.commit()
    logger.info(
        "Formatify task marked canceled | task_id={} | flow_id={} | remote_ok={}",
        formatify_task.id,
        formatify_task.flow_id,
        remote_ok,
    )
    if remote_ok:
        return True, "任务已取消"
    return True, f"任务已取消（CSGHub 停止失败: {remote_err}）"
