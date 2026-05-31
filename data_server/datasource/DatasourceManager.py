import time
from datetime import datetime

from data_server.datasource.DatasourceModels import (DataSource, CollectionTask,
                                                     DataSourceTaskStatusEnum, DataSourceTypeEnum,
                                                     DataSourceStatusEnum)
from data_server.datasource.schemas import DataSourceCreate, DataSourceUpdate
from data_server.database.session import get_sync_session
from sqlalchemy.orm import Session
import json
from typing import List, Tuple, Optional
import uuid, os
from data_server.utils.project_paths import get_datasource_log_path
from data_server.job.SubTaskManager import clear_subtasks_for_parent, replace_subtasks_for_parent
from data_server.utils.csghub_dag_builder import build_datasource_dag
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
from data_server.utils.task_access import (
    apply_active_filter,
    apply_task_list_scope,
    log_task_list_sql,
    resolve_organization_namespace_uuids_for_list,
    soft_delete_record,
    user_can_access_task,
)
from data_server.utils.csghub_namespace import NAMESPACE_TYPE_ORGANIZATION
from data_server.utils.storage_size import normalize_storage_size
from loguru import logger


def apply_cluster_resource_fields(
    target,
    *,
    cluster_id=None,
    cluster_name=None,
    resource_id=None,
    resource_name=None,
    space_resource_id=None,
    storage_size=None,
):
    """Apply region/cloud resource/storage_size from request to DataSource, CollectionTask, or Job."""
    rid = resource_id if resource_id is not None else space_resource_id
    if cluster_id is not None and str(cluster_id).strip() != "":
        target.cluster_id = str(cluster_id).strip()
    if cluster_name is not None and str(cluster_name).strip() != "":
        target.cluster_name = str(cluster_name).strip()
    if rid is not None and str(rid).strip() != "":
        try:
            target.resource_id = int(rid)
        except (TypeError, ValueError):
            target.resource_id = rid
    if resource_name is not None and str(resource_name).strip() != "":
        target.resource_name = str(resource_name).strip()
    if storage_size is not None and str(storage_size).strip() != "":
        target.storage_size = normalize_storage_size(storage_size)


def _mark_collection_task_failed(
    collection_task: CollectionTask,
    error: Exception | str | None = None,
    db_session: Session | None = None,
):
    """On CSGHub main task create/submit failure: mark main task ERROR and clear subtasks."""
    now = datetime.now()
    collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
    collection_task.end_run_at = now
    collection_task.csghub_status = "Failed"
    if db_session is not None and collection_task.id:
        clear_subtasks_for_parent(
            db_session,
            parent_type="datasource",
            parent_id=collection_task.id,
        )
    if error is not None:
        logger.error("Collection task CSGHub submit failed: {}", error)


def greate_task_uid():
    """
    Generate a task UID
    Returns:
        str: The generated task UID
    """
    return str(uuid.uuid4())


def _submit_collection_task_to_csghub(
    db_session: Session,
    collection_task: CollectionTask,
    datasource: DataSource,
    user_token: str | None,
    namespace: str,
    user_name: str | None = None,
    authorization: str | None = None,
):
    flow_id = build_job_flow_id("datasource", collection_task.id)
    collection_task.flow_id = flow_id
    extra_config = datasource.extra_config or {}
    if isinstance(extra_config, str):
        try:
            extra_config = json.loads(extra_config)
        except Exception:
            extra_config = {}
    if not isinstance(extra_config, dict):
        extra_config = {}
    to_repo = extra_config.get("csg_hub_dataset_id")
    to_branch = (
        extra_config.get("csg_hub_dataset_default_branch")
        or extra_config.get("csg_hub_dataset_branch")
        or "main"
    )
    task_params = {
        "collection_task_id": collection_task.id,
        "task_uid": collection_task.task_uid,
        "datasource_id": datasource.id,
        "datasource_name": datasource.name,
        "datasource_des": datasource.des,
        "source_type": datasource.source_type,
        "host": datasource.host,
        "port": datasource.port,
        "username": datasource.username,
        "password": datasource.password,
        "database": datasource.database,
        "auth_type": datasource.auth_type,
        "extra_config": datasource.extra_config,
        "to_csg_hub_repo_id": to_repo,
        "to_csg_hub_dataset_default_branch": to_branch,
        "source_status": datasource.source_status,
        "owner_id": collection_task.owner_id,
        "owner_org_id": collection_task.owner_org_id,
        "owner_org_name": collection_task.owner_org_name,
        "user_name": user_name,
        "user_token": user_token,
        "authorization": authorization,
        "flow_id": flow_id,
        "cluster_id": collection_task.cluster_id,
        "cluster_name": collection_task.cluster_name,
        "resource_id": collection_task.resource_id,
        "resource_name": collection_task.resource_name,
    }
    source_type_mapping = {
        DataSourceTypeEnum.MYSQL.value: "mysql",
        DataSourceTypeEnum.MONGODB.value: "mongo",
        DataSourceTypeEnum.HIVE.value: "hive",
        DataSourceTypeEnum.FILE.value: "file",
    }
    task_params["source_type_name"] = source_type_mapping.get(datasource.source_type, "unknown")
    dag_tasks = build_datasource_dag(flow_id, task_params)
    payload = build_csghub_payload(
        job_id=flow_id,
        job_name=f"datasource-{datasource.name}",
        job_desc=datasource.des or datasource.name,
        resource_id=collection_task.resource_id,
        resource_name=collection_task.resource_name,
        storage_size=getattr(collection_task, "storage_size", None)
        or getattr(datasource, "storage_size", None),
        repo_ids=collect_repo_ids(extra_config=datasource.extra_config),
        dag_tasks=dag_tasks,
    )
    collection_task.csghub_request_payload = json.dumps(payload, ensure_ascii=False)
    response = submit_job_to_csghub(
        payload, namespace=namespace, user_token=user_token, authorization=authorization
    )
    collection_task.csghub_response_payload = json.dumps(response, ensure_ascii=False)
    parsed = ensure_csghub_job_create_success(response)
    collection_task.csghub_job_id = parsed["job_id"]
    collection_task.csghub_status = parsed.get("status") or "Submitted"
    replace_subtasks_for_parent(
        session=db_session,
        parent_type="datasource",
        parent_id=collection_task.id,
        flow_id=flow_id,
        dag_tasks=dag_tasks,
    )
    return response


def create_data_source(
    is_connection: bool,
    db_session: Session,
    datasource: DataSourceCreate,
    user_id,
    user_name: str,
    user_token: str,
    owner_org_id: str | None = None,
    owner_org_name: str | None = None,
    authorization: str | None = None,
):
    """
    Create a data source
    Args:
        datasource (DataSourceCreate): Data source creation parameters
        user_id (int): User ID
        user_name (str): User name
        user_token (str): User token
    Returns:
        int: ID of the created data source
    """
    namespace_uuid, namespace_type = parse_namespace_fields(
        namespace_uuid=datasource.namespace_uuid,
        namespace_type=datasource.namespace_type,
    )
    # create db model
    extra_config = datasource.extra_config or {}
    data_source_db = DataSource(name=datasource.name,
                                des=datasource.des,
                                source_type=datasource.source_type,
                                host=datasource.host,
                                port=datasource.port,
                                username=datasource.username,
                                password=datasource.password,
                                database=datasource.database,
                                auth_type=datasource.auth_type,
                                task_run_time=datasource.task_run_time,
                                extra_config=json.dumps(extra_config, ensure_ascii=False, indent=4),
                                owner_org_id=owner_org_id,
                                owner_org_name=owner_org_name,
                                cluster_id=datasource.cluster_id,
                                cluster_name=datasource.cluster_name,
                                resource_id=datasource.resource_id,
                                resource_name=datasource.resource_name,
                                storage_size=datasource.storage_size,
                                namespace_uuid=namespace_uuid,
                                namespace_type=namespace_type)
    data_source_db.source_status = datasource.source_status
    data_source_db.owner_id = user_id
    db_session.add(data_source_db)
    db_session.commit()
    if datasource.is_run:
        logger.info(f"DataSource{datasource.name} Start executing the task")

        task_uid = greate_task_uid()
        collection_task = CollectionTask(task_uid=task_uid,
                                         datasource_id=data_source_db.id,
                                         task_status=DataSourceTaskStatusEnum.WAITING.value,
                                         total_count=0,
                                         records_count=0,
                                         cluster_id=data_source_db.cluster_id,
                                         cluster_name=data_source_db.cluster_name,
                                         resource_id=data_source_db.resource_id,
                                         resource_name=data_source_db.resource_name,
                                         storage_size=data_source_db.storage_size,
                                         owner_id=user_id,
                                         owner_org_id=owner_org_id,
                                         owner_org_name=owner_org_name,
                                         namespace_uuid=namespace_uuid,
                                         namespace_type=namespace_type)
        db_session.add(collection_task)
        db_session.commit()

        try:
            _submit_collection_task_to_csghub(
                db_session,
                collection_task,
                data_source_db,
                user_token,
                namespace_uuid,
                user_name=user_name,
                authorization=authorization,
            )
            collection_task.task_status = DataSourceTaskStatusEnum.WAITING.value
        except Exception as e:
            _mark_collection_task_failed(collection_task, e, db_session)
            db_session.commit()
            raise
        db_session.commit()
        if is_connection:
            data_source_db.source_status = DataSourceStatusEnum.ACTIVE.value
        else:
            data_source_db.source_status = DataSourceStatusEnum.INACTIVE.value
        db_session.commit()
    return data_source_db.id


def search_data_source(
        user_id,
        session: Session,
        isadmin: bool = False,
        page: int = 1,
        per_page: int = 10,
        name: str = None,
        source_type=None,
        organization_namespace_uuids: list[str] | None = None,
        namespace_uuid: str | None = None,
) -> Tuple[List[DataSource], int]:
    """
    Search data sources

    Args:
        user_id: Header User-Id; same as owner_id when creating data source
        session (Session): Database session
        isadmin (bool): Whether the user is an administrator
        page (int): Current page number, default is 1
        per_page (int): Number of items displayed per page, default is 10

    Returns:
        Tuple[List[DataSource], int]: The first element is the list of searched data sources, the second element is the total number of records
    """

    query = session.query(DataSource)
    query = apply_task_list_scope(
        query,
        DataSource,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
    )
    if name is not None:
        query = query.filter(DataSource.name.like(f"%{name}%"))
    if source_type is not None:
        query = query.filter(DataSource.source_type == source_type)

    log_task_list_sql(
        query,
        label="datasource",
        session=session,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
        page=page,
        per_page=per_page,
        name=name,
        source_type=source_type,
    )

    total_count = query.count()

    data_sources = query.order_by(DataSource.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return data_sources, total_count


def update_data_source(db_session: Session, data_source_id: int, update_data: DataSourceUpdate):
    """
    Update data source record

    Args:
        db_session (Session): Database session
        data_source_id (int): ID of the data source to be updated
        update_data (DataSourceUpdate): Update data

    Returns:
        Optional[DataSource]: The updated data source object, or None if not found
    """

    data_source = db_session.query(DataSource).get(data_source_id)
    if data_source is None:
        return None

    if update_data.name is not None:
        data_source.name = update_data.name
    if update_data.host is not None:
        data_source.host = update_data.host
    if update_data.port is not None:
        data_source.port = update_data.port
    if update_data.username is not None:
        data_source.username = update_data.username
    if update_data.password is not None:
        data_source.password = update_data.password
    if update_data.database is not None:
        data_source.database = update_data.database
    if update_data.auth_type is not None:
        data_source.auth_type = update_data.auth_type
    if update_data.extra_config is not None:
        data_source.extra_config = json.dumps(update_data.extra_config, ensure_ascii=False, indent=4)
    if update_data.namespace_uuid is not None:
        nu, nt = parse_namespace_fields(
            namespace_uuid=update_data.namespace_uuid,
            namespace_type=update_data.namespace_type,
        )
        data_source.namespace_uuid = nu
        data_source.namespace_type = nt
    db_session.commit()

    return data_source


def delete_data_source(db_session: Session, data_source_id: int):
    """
    Delete data source record
    Args:
        db_session (Session): Database session
        data_source_id (int): ID of the data source to be deleted
    Returns:
        bool: Whether the deletion operation is successful
    """

    db_session.query(CollectionTask).filter_by(datasource_id=data_source_id).delete()

    data_source = db_session.query(DataSource).get(data_source_id)
    if data_source is None:
        return False

    db_session.delete(data_source)
    db_session.commit()
    return True


def get_datasource(db_session: Session, datasource_id: int):
    """
    Get data source information
    Args:
        db_session (Session): Database session
        datasource_id (int): Data source ID
    Returns:
        DataSource: Data source object
    """
    data_source = db_session.query(DataSource).get(datasource_id)
    return data_source


def has_execting_tasks(db_session: Session, datasource_id: int):
    """
    Check if the data source has running tasks
    Args:
        db_session (Session): Database session
        datasource_id (int): Data source ID
    Returns:
        bool: Whether there are running tasks
    """
    query = (
        db_session.query(CollectionTask)
        .filter_by(
            datasource_id=datasource_id,
            task_status=DataSourceTaskStatusEnum.EXECUTING.value,
        )
        .filter(CollectionTask.is_active.is_(True))
        .exists()
    )
    return db_session.query(query).scalar()


def get_collection_task(db_session: Session, task_id: int):
    """
    Get collection task information
    Args:
        db_session (Session): Database session
        task_id (int): Task ID
    Returns:
        CollectionTask: Collection task object
    """
    return (
        db_session.query(CollectionTask)
        .filter(CollectionTask.id == task_id, CollectionTask.is_active.is_(True))
        .first()
    )


def get_collection_task_for_user(
    db_session: Session,
    task_id: int,
    user_id,
    isadmin: bool = False,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
    user_name: str | None = None,
    authorization: str | None = None,
    user_token: str | None = None,
) -> CollectionTask | None:
    if organization_namespace_uuids is None and not isadmin:
        organization_namespace_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
    task = get_collection_task(db_session, task_id)
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


def delete_collection_task(db_session: Session, task_id: int) -> bool:
    collection_task = (
        db_session.query(CollectionTask)
        .filter(CollectionTask.id == task_id, CollectionTask.is_active.is_(True))
        .first()
    )
    if collection_task is None:
        return False
    if collection_task.task_status == DataSourceTaskStatusEnum.EXECUTING.value:
        raise ValueError("任务执行中，无法删除")
    soft_delete_record(db_session, collection_task)
    return True


def get_collection_task_by_uid(db_session: Session, task_uid: str):
    """
    Get unique collection task information by task UID

    Args:
        db_session (Session): Database session
        task_uid (str): Task UID

    Returns:
        CollectionTask: Unique collection task object, or None if it does not exist
    """

    collection_task = db_session.query(CollectionTask).filter(CollectionTask.task_uid == task_uid).one_or_none()
    return collection_task


def search_collection_task(
        datasource_id: int,
        session: Session,
        page: int = 1,
        per_page: int = 10,
        user_id=None,
        isadmin: bool = False,
        organization_namespace_uuids: list[str] | None = None,
        namespace_uuid: str | None = None,
) -> Tuple[List[CollectionTask], int]:
    """
    Search the list of tasks under a data source
    Args:
        datasource_id (int): Data source ID
        session (Session): Database session
        page (int): Current page number, default is 1
        per_page (int): Number of items displayed per page, default is 10

    Returns:
        Tuple[List[CollectionTask], int]: The first element is the list of searched data source tasks, the second element is the total number of records
    """
    query = session.query(CollectionTask).filter_by(datasource_id=datasource_id)
    query = apply_task_list_scope(
        query,
        CollectionTask,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
    )
    log_task_list_sql(
        query,
        label="collection",
        session=session,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
        datasource_id=datasource_id,
        page=page,
        per_page=per_page,
    )
    total_count = query.count()
    collection_tasks = (
        query.order_by(CollectionTask.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return collection_tasks, total_count


def search_collection_task_all(
        datasource_id: int,
        session: Session,
) -> Tuple[List[CollectionTask], int]:
    """
    Search the list of tasks under a data source
    Args:
        datasource_id (int): Data source ID
        session (Session): Database session
    Returns:
        Tuple[List[CollectionTask], int]: The first element is the list of searched data source tasks, the second element is the total number of records
    """
    query = session.query(CollectionTask).filter_by(datasource_id=datasource_id)
    query = apply_active_filter(query, CollectionTask)
    total_count = query.count()
    collection_tasks = query.order_by(CollectionTask.created_at).all()
    return collection_tasks, total_count


def execute_collection_task(
    db_session: Session,
    collection_task: CollectionTask,
    user_name: str,
    user_token: str,
    namespace_uuid: str,
    namespace_type: str,
    authorization: str | None = None,
):
    """
    Execute a task
    Args:
        db_session (Session): Database session
        collection_task (CollectionTask): Task object
        user_name (str): User name
        user_token (str): User token
    Returns:
        bool: Whether the execution operation is successful
    """
    try:
        if not collection_task.datasource:
            return False, "Data source does not exist"
        nu, nt = parse_namespace_fields(namespace_uuid=namespace_uuid, namespace_type=namespace_type)
        collection_task.namespace_uuid = nu
        collection_task.namespace_type = nt
        _submit_collection_task_to_csghub(
            db_session,
            collection_task,
            collection_task.datasource,
            user_token,
            nu,
            user_name=user_name,
            authorization=authorization,
        )
        collection_task.task_status = DataSourceTaskStatusEnum.WAITING.value
        db_session.commit()
        return True, None
    except Exception as e:
        _mark_collection_task_failed(collection_task, e, db_session)
        db_session.commit()
        logger.error(f"Execution of the task failed: {str(e)}")
        return False, str(e)


def stop_collection_task(
    db_session: Session,
    collection_task: CollectionTask,
    authorization: str | None = None,
):
    """Cancel collection task: CSGHub DELETE first, then mark canceled locally."""
    namespace_uuid = collection_task.namespace_uuid
    if not namespace_uuid and collection_task.datasource:
        namespace_uuid = collection_task.datasource.namespace_uuid
    resolved_job_id = resolve_csghub_remote_job_id(
        collection_task.csghub_job_id,
        flow_id=collection_task.flow_id,
        csghub_response_payload=collection_task.csghub_response_payload,
    )
    if resolved_job_id:
        collection_task.csghub_job_id = resolved_job_id
    remote_ok, remote_err = try_cancel_csghub_job(
        namespace_uuid=namespace_uuid,
        csghub_job_id=collection_task.csghub_job_id,
        authorization=authorization,
        flow_id=collection_task.flow_id,
        csghub_response_payload=collection_task.csghub_response_payload,
    )
    now = datetime.now()
    collection_task.task_status = DataSourceTaskStatusEnum.STOP.value
    if collection_task.end_run_at is None:
        collection_task.end_run_at = now
    collection_task.csghub_status = "Canceled"
    db_session.commit()
    logger.info(
        "Collection task marked canceled | task_id={} | flow_id={} | remote_ok={}",
        collection_task.id,
        collection_task.flow_id,
        remote_ok,
    )
    if remote_ok:
        return True, "任务已取消"
    return True, f"任务已取消（CSGHub 停止失败: {remote_err}）"


def execute_new_collection_task(
    db_session: Session,
    datasource: DataSource,
    user_name: str,
    user_token: str,
    namespace_uuid: str,
    namespace_type: str,
    authorization: str | None = None,
):
    """
    Execute a task
    Args:
        db_session (Session): Database session
        datasource (DataSource): Data source
        user_name (str): User name
        user_token (str): User token
    Returns:
        bool: Whether the execution operation is successful
    """
    try:

        task_uid = greate_task_uid()
        nu, nt = parse_namespace_fields(namespace_uuid=namespace_uuid, namespace_type=namespace_type)
        datasource.namespace_uuid = nu
        datasource.namespace_type = nt
        collection_task = CollectionTask(task_uid=task_uid,
                                         datasource_id=datasource.id,
                                         task_status=DataSourceTaskStatusEnum.WAITING.value,
                                         total_count=0,
                                         records_count=0,
                                         cluster_id=datasource.cluster_id,
                                         cluster_name=datasource.cluster_name,
                                         resource_id=datasource.resource_id,
                                         resource_name=datasource.resource_name,
                                         storage_size=datasource.storage_size,
                                         owner_id=datasource.owner_id,
                                         owner_org_id=datasource.owner_org_id,
                                         owner_org_name=datasource.owner_org_name,
                                         namespace_uuid=nu,
                                         namespace_type=nt)
        db_session.add(collection_task)
        db_session.commit()
        try:
            _submit_collection_task_to_csghub(
                db_session,
                collection_task,
                datasource,
                user_token,
                nu,
                user_name=user_name,
                authorization=authorization,
            )
            collection_task.task_status = DataSourceTaskStatusEnum.WAITING.value
            db_session.commit()
            return True, None
        except Exception as submit_err:
            _mark_collection_task_failed(collection_task, submit_err, db_session)
            db_session.commit()
            return False, str(submit_err)
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")
        return False, str(e)


def read_task_log(collection_task: CollectionTask):
    """
    Read task log
    Args:
        collection_task (CollectionTask): Task object
    Returns:
        str: Task log
    """
    log_file_path = get_datasource_log_path(collection_task.task_uid)
    try:
        with open(log_file_path, 'r') as f:
            file_content = f.read()
        return True, file_content
    except Exception as e:
        print(f"Failed to query logs: {str(e)}")
        return False, str(e)
