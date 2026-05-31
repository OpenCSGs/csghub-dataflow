import datetime
import asyncio

from fastapi import FastAPI, APIRouter, HTTPException, status, Header, Depends,Body
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from typing import Annotated, Union, Optional
import traceback

from data_server.datasource.schemas import (
    DataSourceCreate, DataSourceUpdate, DataSourceBase
)
from data_server.datasource.services.datasource import get_datasource_connector
from data_server.database.session import get_sync_session

from data_server.datasource.DatasourceManager import (
    create_data_source,
    search_data_source,
    update_data_source,
    delete_data_source,
    get_datasource,
    has_execting_tasks,
    get_collection_task,
    get_collection_task_for_user,
    delete_collection_task,
    execute_collection_task,
    search_collection_task,
    execute_new_collection_task,
    stop_collection_task,
    apply_cluster_resource_fields,
    read_task_log,
    search_collection_task_all,
)
from data_server.utils.task_access import (
    attach_can_delete,
    can_delete_task,
    normalize_user_id,
    resolve_organization_namespace_uuids_for_list,
)
from data_server.schemas.responses import response_success, response_fail
from data_server.datasource.DatasourceModels import DataSourceTypeEnum, DataSourceStatusEnum, DataSourceTaskStatusEnum, \
    CollectionTask
from data_server.utils.csghub_namespace import parse_namespace_fields
from data_server.utils.csghub_status_sync import (
    should_query_csghub_status,
    sync_csghub_main_task_status_by_query,
)
from data_server.job.SubTaskManager import (
    count_subtasks_for_parent,
    get_subtask_for_parent,
    list_subtasks_for_parent,
)
from data_server.utils.csghub_client import resolve_csghub_remote_job_id
from data_server.utils.csghub_task_logs import fetch_csghub_logs_payload
from loguru import logger

app = FastAPI(title="数据采集系统API")
router = APIRouter()


def _collection_task_main_log_api(task_id: int) -> str:
    return f"/datasource/tasks/{task_id}/logs"


def _collection_subtask_log_api(task_id: int, dag_task_id: str) -> str:
    return f"/datasource/tasks/{task_id}/subtasks/{dag_task_id}/logs"


def _fetch_collection_task_logs(
    collection_task: CollectionTask,
    db: Session,
    *,
    dag_task_id: str | None,
    stream: bool,
    user_token: str | None,
    authorization: str | None,
) -> dict:
    """Main task log when dag_task_id=None; pass dag_task_id for subtask log."""
    has_csghub = bool(collection_task.csghub_job_id)
    logger.info(
        "collection task logs fetch | task_id={tid} | has_csghub_job_id={has_csghub} | "
        "csghub_job_id={cjid} | flow_id={fid} | namespace_uuid={ns} | dag_task_id={dag} | "
        "stream={stream} | has_user_token={ut} | has_authorization={auth}",
        tid=collection_task.id,
        has_csghub=has_csghub,
        cjid=collection_task.csghub_job_id or "(empty)",
        fid=collection_task.flow_id or "(empty)",
        ns=collection_task.namespace_uuid or "(empty)",
        dag=dag_task_id or "(main)",
        stream=stream,
        ut=bool(str(user_token or "").strip()),
        auth=bool(str(authorization or "").strip()),
    )
    if collection_task.csghub_job_id:
        logger.info(
            "collection task logs branch=csghub | task_id={tid}",
            tid=collection_task.id,
        )
        if dag_task_id:
            subtask = get_subtask_for_parent(
                db,
                parent_type="datasource",
                parent_id=collection_task.id,
                dag_task_id=dag_task_id,
            )
            if subtask is None:
                raise ValueError(f"子任务不存在: {dag_task_id}")
        data = fetch_csghub_logs_payload(
            namespace_uuid=collection_task.namespace_uuid,
            csghub_job_id=collection_task.csghub_job_id,
            flow_id=collection_task.flow_id,
            csghub_response_payload=collection_task.csghub_response_payload,
            dag_task_id=dag_task_id,
            stream=stream,
            user_token=user_token,
            authorization=authorization,
        )
        data["source"] = "csghub"
        data["log_api"] = (
            _collection_subtask_log_api(collection_task.id, dag_task_id)
            if dag_task_id
            else _collection_task_main_log_api(collection_task.id)
        )
        logger.info(
            "collection task logs csghub result | task_id={tid} | scope={scope} | "
            "logs_len={logs_len} | remote_job_id={remote}",
            tid=collection_task.id,
            scope=data.get("scope"),
            logs_len=len(data.get("logs") or ""),
            remote=data.get("csghub_job_id"),
        )
        return data

    logger.info(
        "collection task logs branch=local | task_id={tid} | task_uid={uid}",
        tid=collection_task.id,
        uid=collection_task.task_uid or "(empty)",
    )
    if dag_task_id:
        raise ValueError("任务未提交到 CSGHub，无法按子任务查询远端日志")

    result, content = read_task_log(collection_task)
    if not result:
        raise RuntimeError(f"读取日志失败:{content}")
    if not content:
        raise ValueError(f"任务 {collection_task.id} 日志不存在")
    logger.info(
        "collection task logs local result | task_id={tid} | logs_len={logs_len}",
        tid=collection_task.id,
        logs_len=len(content or ""),
    )
    return {
        "logs": content,
        "scope": "main",
        "source": "local",
        "dag_task_id": None,
        "stream": stream,
        "log_api": _collection_task_main_log_api(collection_task.id),
    }


def _enrich_collection_task_for_list(
    task_dict: dict,
    task: CollectionTask | None = None,
    *,
    user_id=None,
    isadmin: bool = False,
) -> dict:
    task_id = task_dict.get("id")
    has_csghub = bool(task_dict.get("csghub_job_id"))
    task_dict["logs_available"] = has_csghub or bool(task_dict.get("task_uid"))
    task_dict["main_log_api"] = _collection_task_main_log_api(task_id) if task_id else None
    task_dict["subtasks_api"] = f"/datasource/tasks/{task_id}/subtasks" if task_id else None
    if task and task.csghub_job_id:
        task_dict["csghub_remote_job_id"] = resolve_csghub_remote_job_id(
            task.csghub_job_id,
            flow_id=task.flow_id,
            csghub_response_payload=task.csghub_response_payload,
        )
    owner_id = task_dict.get("owner_id") if task is None else task.owner_id
    attach_can_delete(task_dict, owner_id=owner_id, user_id=user_id, isadmin=isadmin)
    return task_dict


def _enrich_collection_subtask_for_list(task_id: int, subtask: dict) -> dict:
    dag_task_id = subtask.get("task_id")
    if dag_task_id:
        subtask["dag_task_id"] = dag_task_id
        subtask["log_api"] = _collection_subtask_log_api(task_id, dag_task_id)
    return subtask


@router.get("/datasource/get_data_source_type_list", response_model=dict)
async def get_data_source_type_list():

    # data_source_types = [
    #     {"id": type.value, "name": type.name.capitalize()}
    #     for type in DataSourceTypeEnum
    # ]
    data_source_types = [
        {
            "id": DataSourceTypeEnum.MYSQL.value,
            "name": DataSourceTypeEnum.MYSQL.name.capitalize(),
            "title": "关系型数据库(MySQL)",
            "desc": "批量导入数据库表，支持自定义表、字段"
        },
        {
            "id": DataSourceTypeEnum.MONGODB.value,
            "name": DataSourceTypeEnum.MONGODB.name.capitalize(),
            "title": "非关系型数据库(MongoDB)",
            "desc": "导入非关系型数据，支持集合、字段选择和结构转换"
        },
        {
            "id": DataSourceTypeEnum.FILE.value,
            "name": DataSourceTypeEnum.FILE.name.capitalize(),
            "title": "文件数据导入",
            "desc": "支持CSV、Excel、JSON等多种格式文件导入"
        },
        {
            "id": DataSourceTypeEnum.HIVE.value,
            "name": DataSourceTypeEnum.HIVE.name.capitalize(),
            "title": "Hive系统导入",
            "desc": "高效读取hive系统中存储的数据"
        }
    ]
    return response_success(data=data_source_types)


@router.get("/get_task_statistics", response_model=dict)
async def get_task_statistics(db: Session = Depends(get_sync_session)):
    status_counts = db.query(
        CollectionTask.task_status,
        func.count(CollectionTask.id).label('count')
    ).group_by(CollectionTask.task_status).all()
    statistics = {}
    for status, count in status_counts:
        status_name = DataSourceTaskStatusEnum(status).name
        statistics[status_name] = count
    for status_enum in DataSourceTaskStatusEnum:
        if status_enum.name not in statistics:
            statistics[status_enum.name] = 0
    return response_success(data=statistics)


@router.post("/datasource/create", response_model=dict)
async def create_datasource(datasource: DataSourceCreate, db: Session = Depends(get_sync_session),
                            user_name: Annotated[str | None, Header(alias="User-Name")] = None,
                            user_id: Annotated[str | None, Header(alias="User-Id")] = None,
                            user_token: Annotated[str | None, Header(alias="User-Token")] = None,
                            authorization: Annotated[str | None, Header(alias="Authorization")] = None,
                            owner_org_id: Annotated[str | None, Header(alias="Org-Id")] = None,
                            owner_org_name: Annotated[str | None, Header(alias="Org-Name")] = None
                            ):

    try:
        if datasource.source_type not in [item.value for item in DataSourceTypeEnum]:
            return response_fail(msg="不支持的数据源类型")
        # user_id = 54
        
        # Handle branch information: correct branch information passed from frontend
        # Frontend may incorrectly place user-entered branch name in csg_hub_dataset_name
        if datasource.extra_config is None:
            datasource.extra_config = {}
        
        current_branch = datasource.extra_config.get("csg_hub_dataset_default_branch", "")
        dataset_name = datasource.extra_config.get("csg_hub_dataset_name", "")
        dataset_id = datasource.extra_config.get("csg_hub_dataset_id", "")
        
        # If user selected data flow direction, branch is main, but dataset_name has value, use dataset_name as branch
        if dataset_id and current_branch == "main" and dataset_name and dataset_name != "main" and dataset_name.strip():
            datasource.extra_config["csg_hub_dataset_default_branch"] = dataset_name

        connector = get_datasource_connector(datasource)
        # Run the synchronized test_connection method in the thread pool
        loop = asyncio.get_event_loop()
        test_result = await loop.run_in_executor(None, connector.test_connection)
        if not test_result.get('success', False):
            datasource.source_status = DataSourceStatusEnum.INACTIVE.value
        else:
            if datasource.is_run:
                datasource.source_status = DataSourceStatusEnum.ACTIVE.value
            else:
                datasource.source_status = DataSourceStatusEnum.WAITING.value
        if not user_id:
            return response_fail(msg="用户ID不能为空")
        try:
            parse_namespace_fields(
                namespace_uuid=datasource.namespace_uuid,
                namespace_type=datasource.namespace_type,
            )
        except ValueError as e:
            return response_fail(msg=str(e))
        data_source_id = create_data_source(
            test_result, db, datasource, int(user_id), user_name, user_token,
            owner_org_id=owner_org_id, owner_org_name=owner_org_name,
            authorization=authorization,
        )
        return response_success(data=data_source_id)
    except Exception as e:
        logger.error(f"Failed to create datasource: {str(e)}- {traceback.print_exc()}")
        return response_fail(msg="创建数据源失败")


@router.get("/datasource/list", response_model=dict)
async def datasource_list(
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    page: int = 0,
    pageSize: int = 20,
    name: str = None,
    source_type=None,
    db: Session = Depends(get_sync_session),
):
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        data_sources, total = search_data_source(
            user_id,
            db,
            isadmin,
            page,
            pageSize,
            name,
            source_type,
            organization_namespace_uuids=org_uuids,
        )
        data_sources = [item.to_json() for item in data_sources]
        return response_success(data={
            "list": data_sources,
            "total": total
        })
    except Exception as e:
        logger.error(f"Failed to datasource_list: {str(e)}")
        return response_fail(msg="查询失败")
    finally:
        db.close()

@router.post("/datasource/test-connection", response_model=dict)
async def test_datasource_connection(datasource: DataSourceBase):

    try:
        connector = get_datasource_connector(datasource)
        # Run the synchronized test_connection method in the thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, connector.test_connection)
        return response_success(data=result)
    except Exception as e:
        logger.error(f"test_datasource_connection: {str(e)}")
        return response_fail(msg=f"测试连接失败:{str(e)}")


@router.put("/datasource/edit/{datasource_id}", response_model=dict)
async def update_datasource(datasource_id: int, datasource: DataSourceUpdate, db: Session = Depends(get_sync_session)):
    try:
        # Handle branch information: correct branch information passed from frontend (same logic as create interface)
        if datasource.extra_config is not None:
            current_branch = datasource.extra_config.get("csg_hub_dataset_default_branch", "")
            dataset_name = datasource.extra_config.get("csg_hub_dataset_name", "")
            dataset_id = datasource.extra_config.get("csg_hub_dataset_id", "")
            
            # If user selected data flow direction, branch is main, but dataset_name has value, use dataset_name as branch
            if dataset_id and current_branch == "main" and dataset_name and dataset_name != "main" and dataset_name.strip():
                datasource.extra_config["csg_hub_dataset_default_branch"] = dataset_name
        
        data_source = update_data_source(db, datasource_id, datasource)
        if not data_source:
            return response_fail(msg="更新失败")
        return response_success(data=data_source)
    except Exception as e:
        logger.error(f"update_datasource: {str(e)}")
        return response_fail(msg=f"更新失败:{str(e)}")


@router.delete("/datasource/remove/{datasource_id}", response_model=dict)
async def delete_datasource(datasource_id: int, db: Session = Depends(get_sync_session)):

    try:

        if has_execting_tasks(db, datasource_id):
            return response_fail(msg="存在执行中的任务，无法删除")
        result = delete_data_source(db, datasource_id)
        if not result:
            return response_fail(msg="删除失败")
        return response_success(data=result)
    except Exception as e:
        logger.error(f"delete_datasource: {str(e)}")
        return response_fail(msg=f"更新失败:{str(e)}")


@router.post("/datasource/execute/{datasource_id}", description="数据源执行新采集任务", response_model=dict)
async def datasource_run_task(datasource_id: int,
                              data: dict = Body(...),
                              db: Session = Depends(get_sync_session),
                              user_name: Annotated[str | None, Header(alias="User-Name")] = None,
                              user_id: Annotated[str | None, Header(alias="User-Id")] = None,
                              user_token: Annotated[str | None, Header(alias="User-Token")] = None,
                              authorization: Annotated[str | None, Header(alias="Authorization")] = None,
                              ):


    datasource = get_datasource(db, datasource_id)
    if not datasource:
        return response_fail(msg="数据源不存在")

    if has_execting_tasks(db, datasource_id):
        return response_fail(msg="存在执行中的任务，无法执行")

    task_run_time = data.get("task_run_time")
    if task_run_time:
        datasource.task_run_time = datetime.datetime.strptime(task_run_time, "%Y-%m-%d %H:%M:%S")
    else:
        datasource.task_run_time = None
    apply_cluster_resource_fields(
        datasource,
        cluster_id=data.get("cluster_id"),
        cluster_name=data.get("cluster_name"),
        resource_id=data.get("resource_id"),
        resource_name=data.get("resource_name"),
        space_resource_id=data.get("space_resource_id"),
        storage_size=data.get("storage_size"),
    )
    db.commit()
    # Datasource list Execute: namespace from DB config at creation time, not request body
    result, msg = execute_new_collection_task(
        db,
        datasource,
        user_name,
        user_token,
        getattr(datasource, "namespace_uuid", None),
        getattr(datasource, "namespace_type", None),
        authorization=authorization,
    )
    if result:
        return response_success(data="任务执行成功")
    return response_fail(msg="任务执行失败:" + msg)



@router.post("/datasource/tables", response_model=dict)
async def get_datasource_tables(datasource: DataSourceBase):

    try:
        # if datasource.source_type == DataSourceTypeEnum.MONGODB.value:

        connector = get_datasource_connector(datasource)
        # test_the_connection_in_the_thread_pool
        loop = asyncio.get_event_loop()
        test_result = await loop.run_in_executor(None, connector.test_connection)
        if not test_result.get('success', False):
            return response_fail(msg="数据源连接失败")

        tables = await loop.run_in_executor(None, connector.get_tables)
        return response_success(data=tables)
    except Exception as e:
        logger.error(f"Failed to get table list: {str(e)}")
        return response_fail(msg=f"获取表列表失败: {str(e)}")


@router.post("/datasource/table_columns", response_model=dict)
async def get_datasource_table_columns(datasource: DataSourceBase, table_name: str):

    try:
        if datasource.source_type == DataSourceTypeEnum.MONGODB.value:
            return response_fail(msg="MongoDB不支持获取表和字段列表")

        connector = get_datasource_connector(datasource)
        loop = asyncio.get_event_loop()
        test_result = await loop.run_in_executor(None, connector.test_connection)
        if not test_result.get('success', False):
            return response_fail(msg="数据源连接失败")

        columns = await loop.run_in_executor(None, connector.get_table_columns, table_name)
        return response_success(data=columns)
    except Exception as e:
        logger.error(f"Failed to get table columns: {str(e)}")
        return response_fail(msg=f"获取表字段失败: {str(e)}")


@router.get("/datasource/info", response_model=dict)
async def get_datasource_info(
    datasource_id: int,
    db: Session = Depends(get_sync_session),
):
    datasource = get_datasource(db, datasource_id)
    task_list, task_total = search_collection_task_all(datasource_id, db)
    last_task = task_list[-1] if task_list else None
    return response_success(data={
        'datasourceInfo': datasource.to_json(),
        'task_total': task_total,
        'last_task': last_task.to_dict() if last_task else None,
    })



@router.post("/datasource/tables_and_columns", response_model=dict)
async def get_datasource_tables_and_columns(datasource: DataSourceBase):

    try:
        if datasource.source_type == DataSourceTypeEnum.MONGODB.value:
            return response_fail(msg="MongoDB不支持获取表和字段列表")

        connector = get_datasource_connector(datasource)
        test_result = connector.test_connection()
        if not test_result or not test_result.get("success", False):
            error_msg = test_result.get("message", "Connection failed") if test_result else "Connection test returned None"
            return response_fail(msg=f"数据源连接失败: {error_msg}")

        tables_and_columns = connector.get_tables_and_columns()
        return response_success(data=tables_and_columns)
    except Exception as e:
        logger.error(f"Failed to get tables and columns: {str(e)}")
        return response_fail(msg=f"获取表和字段列表失败: {str(e)}")



@router.get("/collectiontasks/list", response_model=dict)
async def collection_task_list(
    datasource_id: int,
    page: int = 0,
    pageSize: int = 20,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    db: Session = Depends(get_sync_session),
):
    try:
        datasource = get_datasource(db, datasource_id)
        if not datasource:
            return response_fail(msg="数据源不存在")
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        collection_tasks, total = search_collection_task(
            datasource_id,
            db,
            page,
            pageSize,
            user_id=user_id,
            isadmin=isadmin,
            organization_namespace_uuids=org_uuids,
        )
        uid = normalize_user_id(user_id)
        task_payloads = []
        for task in collection_tasks:
            task_dict = task.to_dict()
            task_dict["subtask_count"] = (
                count_subtasks_for_parent(
                    db,
                    parent_type="datasource",
                    parent_id=task.id,
                )
                if task.csghub_job_id
                else 0
            )
            task_payloads.append(
                _enrich_collection_task_for_list(
                    task_dict, task, user_id=uid, isadmin=isadmin
                )
            )
        return response_success(data={
            "list": task_payloads,
            "total": total
        })
    except Exception as e:
        logger.error(f"Failed to collection_task list: {str(e)}")
        return response_fail(msg="查询失败")


@router.delete("/collection/task/{task_id}", response_model=dict, description="逻辑删除采集任务")
async def delete_collection_task_api(
    task_id: int,
    user_id: Annotated[str | None, Header(alias="User-Id")] = None,
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None,
    user_name: Annotated[str | None, Header(alias="User-Name")] = None,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_sync_session),
):
    try:
        org_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
        task = get_collection_task_for_user(
            db,
            task_id,
            user_id,
            isadmin,
            organization_namespace_uuids=org_uuids,
        )
        if not task:
            return response_fail(msg="任务不存在或无权访问")
        if not can_delete_task(owner_id=task.owner_id, user_id=user_id, isadmin=isadmin):
            return response_fail(msg="仅任务创建者或管理员可删除")
        delete_collection_task(db, task_id)
        return response_success(data=True)
    except ValueError as e:
        return response_fail(msg=str(e))
    except Exception as e:
        logger.error(f"delete_collection_task failed: {e}")
        return response_fail(msg=f"删除失败: {str(e)}")



@router.get("/collection/task", response_model=dict, description="采集任务详情；sync_status=true 时按条件向 CSGHub 拉取状态")
async def get_collection_task_details(
    task_id: int,
    sync_status: bool = False,
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_sync_session),
):

    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        if sync_status and should_query_csghub_status(collection_task, "datasource"):
            sync_csghub_main_task_status_by_query(
                db,
                flow_id=collection_task.flow_id,
                csghub_job_id=collection_task.csghub_job_id,
                user_token=user_token,
                authorization=authorization,
                csghub_response_payload=collection_task.csghub_response_payload,
            )
            db.refresh(collection_task)
        return response_success(data=collection_task.to_dict())
    except Exception as e:
        logger.error(f"Failed to collection_task: {str(e)}")
        return response_fail(msg="查询失败")


@router.get("/tasks/{task_id}/subtasks", response_model=dict)
async def list_collection_task_subtasks(
    task_id: int,
    db: Session = Depends(get_sync_session),
):
    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        # Do not return subtasks when main task was not submitted to CSGHub (creation failed)
        if not collection_task.csghub_job_id:
            return response_success(data={"list": [], "total": 0})
        subtasks = list_subtasks_for_parent(
            db,
            parent_type="datasource",
            parent_id=collection_task.id,
        )
        enriched = [
            _enrich_collection_subtask_for_list(task_id, item)
            for item in subtasks
        ]
        return response_success(
            data={
                "list": enriched,
                "total": len(enriched),
                "main_log_api": _collection_task_main_log_api(task_id),
            }
        )
    except Exception as e:
        logger.error(f"list_collection_task_subtasks failed: {e}")
        return response_fail(msg="查询子任务失败")


@router.post("/tasks/execute/{task_id}", response_model=dict)
async def run_task(task_id: int,
                   data: dict = Body(default={}),
                   db: Session = Depends(get_sync_session),
                   user_name: Annotated[str | None, Header(alias="User-Name")] = None,
                   user_id: Annotated[str | None, Header(alias="User-Id")] = None,
                   user_token: Annotated[str | None, Header(alias="User-Token")] = None,
                   authorization: Annotated[str | None, Header(alias="Authorization")] = None,
                   ):

    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        if collection_task.task_status == DataSourceTaskStatusEnum.EXECUTING.value:
            return response_fail(msg="该任务在执行中")
        apply_cluster_resource_fields(
            collection_task,
            cluster_id=data.get("cluster_id"),
            cluster_name=data.get("cluster_name"),
            resource_id=data.get("resource_id"),
            resource_name=data.get("resource_name"),
            space_resource_id=data.get("space_resource_id"),
            storage_size=data.get("storage_size"),
        )
        if collection_task.datasource:
            apply_cluster_resource_fields(
                collection_task.datasource,
                cluster_id=data.get("cluster_id"),
                cluster_name=data.get("cluster_name"),
                resource_id=data.get("resource_id"),
                resource_name=data.get("resource_name"),
                space_resource_id=data.get("space_resource_id"),
                storage_size=data.get("storage_size"),
            )
        db.commit()

        if collection_task.task_status == DataSourceTaskStatusEnum.WAITING.value:
            if collection_task.csghub_job_id:
                return response_fail(msg="任务已在等待执行，无需重复提交")
            result, msg = execute_collection_task(
                db,
                collection_task,
                user_name,
                user_token,
                data.get("namespace_uuid") or collection_task.namespace_uuid,
                data.get("namespace_type") or collection_task.namespace_type,
                authorization=authorization,
            )
        else:
            datasource = collection_task.datasource
            if not datasource:
                return response_fail(msg="数据源不存在")
            result, msg = execute_new_collection_task(
                db,
                datasource,
                user_name,
                user_token,
                data.get("namespace_uuid") or datasource.namespace_uuid,
                data.get("namespace_type") or datasource.namespace_type,
                authorization=authorization,
            )
        if result:
            return response_success(data="任务执行成功")
        return response_fail(msg="任务执行失败:" + msg)
    except Exception as e:
        logger.error(f"Failed to execute task: {str(e)}")
        return response_fail(msg="任务执行失败")


@router.post("/tasks/stop/{task_id}", response_model=dict)
async def stop_task(
    task_id: int,
    db: Session = Depends(get_sync_session),
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):

    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        if collection_task.task_status not in (
            DataSourceTaskStatusEnum.EXECUTING.value,
            DataSourceTaskStatusEnum.WAITING.value,
        ):
            return response_fail(msg="该任务执行已结束")
        result, msg = stop_collection_task(db, collection_task, authorization=authorization)
        if result:
            return response_success(data=msg or "任务停止成功")
        return response_fail(msg=msg or "任务停止失败")
    except Exception as e:
        logger.error(f"Failed to stop task: {str(e)}")
        return response_fail(msg="任务停止失败")


@router.get("/tasks/{task_id}/logs", response_model=dict)
async def read_collection_task_main_log(
    task_id: int,
    stream: bool = False,
    db: Session = Depends(get_sync_session),
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    """Collection task list - main task log (CSGHub full / local celery log)."""
    logger.info(
        "datasource log API hit | route=main | task_id={tid} | stream={stream}",
        tid=task_id,
        stream=stream,
    )
    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        data = _fetch_collection_task_logs(
            collection_task,
            db,
            dag_task_id=None,
            stream=stream,
            user_token=user_token,
            authorization=authorization,
        )
        return response_success(data=data)
    except ValueError as exc:
        return response_fail(msg=str(exc))
    except RuntimeError as exc:
        return response_fail(msg=str(exc))
    except Exception as e:
        logger.error(f"Failed to read main task log: {str(e)}")
        return response_fail(msg="读取日志失败")


@router.get("/tasks/{task_id}/subtasks/{dag_task_id}/logs", response_model=dict)
async def read_collection_subtask_log(
    task_id: int,
    dag_task_id: str,
    stream: bool = False,
    db: Session = Depends(get_sync_session),
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    """Collection task list - single subtask log (CSGHub dag_task_id)."""
    logger.info(
        "datasource log API hit | route=subtask | task_id={tid} | dag_task_id={dag} | stream={stream}",
        tid=task_id,
        dag=dag_task_id,
        stream=stream,
    )
    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        data = _fetch_collection_task_logs(
            collection_task,
            db,
            dag_task_id=dag_task_id,
            stream=stream,
            user_token=user_token,
            authorization=authorization,
        )
        return response_success(data=data)
    except ValueError as exc:
        return response_fail(msg=str(exc))
    except RuntimeError as exc:
        return response_fail(msg=str(exc))
    except Exception as e:
        logger.error(f"Failed to read subtask log: {str(e)}")
        return response_fail(msg="读取日志失败")


@router.get("/tasks/log/{task_id}", response_model=dict)
async def read_log(
    task_id: int,
    dag_task_id: str | None = None,
    stream: bool = False,
    db: Session = Depends(get_sync_session),
    user_token: Annotated[str | None, Header(alias="User-Token")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    """
    Legacy path. Prefer:
    - Main task: GET /tasks/{task_id}/logs
    - Subtask: GET /tasks/{task_id}/subtasks/{dag_task_id}/logs
    """
    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        data = _fetch_collection_task_logs(
            collection_task,
            db,
            dag_task_id=dag_task_id,
            stream=stream,
            user_token=user_token,
            authorization=authorization,
        )
        return response_success(data=data)
    except ValueError as exc:
        return response_fail(msg=str(exc))
    except RuntimeError as exc:
        return response_fail(msg=str(exc))
    except Exception as e:
        logger.error(f"Failed to read log: {str(e)}")
        return response_fail(msg="读取日志失败")
