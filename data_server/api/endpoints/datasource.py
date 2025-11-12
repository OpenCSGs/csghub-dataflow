import datetime
import asyncio

from fastapi import FastAPI, APIRouter, HTTPException, status, Header, Depends,Body
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from typing import Annotated, Union
import traceback

from data_server.datasource.schemas import (
    DataSourceCreate, DataSourceUpdate
)
from data_server.datasource.services.datasource import get_datasource_connector
from data_server.database.session import get_sync_session

from data_server.datasource.DatasourceManager import (create_data_source, search_data_source,
                                                      update_data_source, delete_data_source,
                                                      get_datasource, has_execting_tasks, get_collection_task,
                                                      execute_collection_task, search_collection_task,
                                                      execute_new_collection_task, stop_collection_task,
                                                      read_task_log, search_collection_task_all)
from data_server.schemas.responses import response_success, response_fail
from data_server.datasource.DatasourceModels import DataSourceTypeEnum, DataSourceStatusEnum, DataSourceTaskStatusEnum, \
    CollectionTask
from loguru import logger

app = FastAPI(title="数据采集系统API")
router = APIRouter()




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
                            user_name: Annotated[str | None, Header(alias="user_name")] = None,
                            user_id: Annotated[str | None, Header(alias="user_id")] = None,
                            user_token: Annotated[str | None, Header(alias="user_token")] = None
                            ):

    try:
        if datasource.source_type not in [item.value for item in DataSourceTypeEnum]:
            return response_fail(msg="不支持的数据源类型")
        # user_id = 54
        
        # 处理分支信息：修正前端传递的分支信息
        # 前端可能将用户填写的分支名错误地放在了 csg_hub_dataset_name 中
        if datasource.extra_config is None:
            datasource.extra_config = {}
        
        current_branch = datasource.extra_config.get("csg_hub_dataset_default_branch", "")
        dataset_name = datasource.extra_config.get("csg_hub_dataset_name", "")
        dataset_id = datasource.extra_config.get("csg_hub_dataset_id", "")
        
        # 如果用户选择了数据流向，且分支是 main，但 dataset_name 有值，使用 dataset_name 作为分支
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
        data_source_id = create_data_source(test_result, db, datasource, int(user_id), user_name,
                                            user_token)
        return response_success(data=data_source_id)
    except Exception as e:
        logger.error(f"Failed to create datasource: {str(e)}- {traceback.print_exc()}")
        return response_fail(msg="创建数据源失败")


@router.get("/datasource/list", response_model=dict)
async def datasource_list(user_id: Annotated[str | None,
Header(alias="user_id")] = None,
                          isadmin: Annotated[bool | None,
                          Header(alias="isadmin")] = None,
                          page: int = 0, pageSize: int = 20,
                          name: str = None,
                          source_type = None,
                          db: Session = Depends(get_sync_session)):


    try:
        if user_id is None or user_id == "":
            user_id_int = 0
        else:
            user_id_int = int(user_id)
        data_sources, total = search_data_source(user_id_int, db, isadmin, page, pageSize, name, source_type)
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
async def test_datasource_connection(datasource: DataSourceCreate):

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
        # 处理分支信息：修正前端传递的分支信息（与创建接口相同的逻辑）
        if datasource.extra_config is not None:
            current_branch = datasource.extra_config.get("csg_hub_dataset_default_branch", "")
            dataset_name = datasource.extra_config.get("csg_hub_dataset_name", "")
            dataset_id = datasource.extra_config.get("csg_hub_dataset_id", "")
            
            # 如果用户选择了数据流向，且分支是 main，但 dataset_name 有值，使用 dataset_name 作为分支
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
                              user_name: Annotated[str | None, Header(alias="user_name")] = None,
                              user_token: Annotated[str | None, Header(alias="user_token")] = None
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
    result, msg = execute_new_collection_task(db, datasource, user_name, user_token)
    if result:
        return response_success(data="任务执行成功")
    return response_fail(msg="任务执行失败:" + msg)



@router.post("/datasource/tables", response_model=dict)
async def get_datasource_tables(datasource: DataSourceCreate):

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
        logger.error(f"获取表列表失败: {str(e)}")
        return response_fail(msg=f"获取表列表失败: {str(e)}")


@router.post("/datasource/table_columns", response_model=dict)
async def get_datasource_table_columns(datasource: DataSourceCreate, table_name: str):

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
        logger.error(f"获取表字段失败: {str(e)}")
        return response_fail(msg=f"获取表字段失败: {str(e)}")


@router.get("/datasource/info", response_model=dict)
async def get_datasource_info(datasource_id: int, db: Session = Depends(get_sync_session)):
    datasource = get_datasource(db, datasource_id)
    task_list, task_total = search_collection_task_all(datasource_id, db)
    return response_success(data={
        'datasourceInfo': datasource.to_json(),
        'task_total': task_total,
        'last_task': task_list[-1].to_dict() if task_list else None,
    })



@router.post("/datasource/tables_and_columns", response_model=dict)
async def get_datasource_tables_and_columns(datasource: DataSourceCreate):

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
        logger.error(f"获取表和字段列表失败: {str(e)}")
        return response_fail(msg=f"获取表和字段列表失败: {str(e)}")



@router.get("/collectiontasks/list", response_model=dict)
async def collection_task_list(datasource_id: int,
                               page: int = 0, pageSize: int = 20,
                               db: Session = Depends(get_sync_session)):

    try:
        datasource = get_datasource(db, datasource_id)
        if not datasource:
            return response_fail(msg="数据源不存在")
        collection_tasks, total = search_collection_task(datasource_id, db, page, pageSize)
        return response_success(data={
            "list": [task.to_dict() for task in collection_tasks],
            "total": total
        })
    except Exception as e:
        logger.error(f"Failed to collection_task list: {str(e)}")
        return response_fail(msg="查询失败")



@router.get("/collection/task", response_model=dict)
async def get_collection_task_details(task_id: int,
                                      db: Session = Depends(get_sync_session)):

    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        return response_success(data=collection_task)
    except Exception as e:
        logger.error(f"Failed to collection_task: {str(e)}")
        return response_fail(msg="查询失败")


@router.post("/tasks/execute/{task_id}", response_model=dict)
async def run_task(task_id: int, db: Session = Depends(get_sync_session),
                   user_name: Annotated[str | None, Header(alias="user_name")] = None,
                   user_token: Annotated[str | None, Header(alias="user_token")] = None
                   ):

    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        if collection_task.task_status == DataSourceTaskStatusEnum.EXECUTING:
            return response_fail(msg="该任务在执行中")
        if collection_task.task_status == DataSourceTaskStatusEnum.WAITING:
            return response_fail(msg="该任务已等待执行")
        result, msg = execute_collection_task(db, collection_task, user_name, user_token)
        if result:
            return response_success(data="任务执行成功")
        return response_fail(msg="任务执行失败:" + msg)
    except Exception as e:
        logger.error(f"执行任务失败: {str(e)}")
        return response_fail(msg="任务执行失败")


@router.post("/tasks/stop/{task_id}", response_model=dict)
async def stop_task(task_id: int, db: Session = Depends(get_sync_session)):

    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        if collection_task.task_status != DataSourceTaskStatusEnum.EXECUTING.value:
            return response_fail(msg="该任务执行已结束")
        result, msg = stop_collection_task(db, collection_task)
        if result:
            return response_success(data="任务停止成功")
        return response_fail(msg="任务停止成功:" + msg)
    except Exception as e:
        logger.error(f"执行停止失败: {str(e)}")
        return response_fail(msg="任务停止失败")


@router.get("/tasks/log/{task_id}", response_model=dict)
async def read_log(task_id: int, db: Session = Depends(get_sync_session)):

    try:
        collection_task = get_collection_task(db, task_id)
        if not collection_task:
            return response_fail(msg="任务不存在")
        result, content = read_task_log(collection_task)
        if not result:
            return response_fail(msg=f"读取日志失败:{content}")
        if not content:
            return response_fail(msg=f"任务 {task_id} 日志不存在")
        return content
    except Exception as e:
        logger.error(f"读取日志失败: {str(e)}")
        return response_fail(msg="读取日志失败")
