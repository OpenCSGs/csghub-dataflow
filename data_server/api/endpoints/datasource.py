from fastapi import FastAPI, APIRouter, HTTPException, status, Header, Depends
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


# 数据源管理API

@router.get("/datasource/get_data_source_type_list", response_model=dict)
async def get_data_source_type_list():
    """
    获取数据源类型列表
    Returns:
        Dict: 包含数据源类型列表的响应
    """
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


@router.post("/datasource/create", response_model=dict)
async def create_datasource(datasource: DataSourceCreate, db: Session = Depends(get_sync_session),
                            user_name: Annotated[str | None, Header(alias="user_name")] = None,
                            user_id: Annotated[str | None, Header(alias="user_id")] = None,
                            user_token: Annotated[str | None, Header(alias="user_token")] = None
                            ):
    """
    创建数据源
    Args:
        datasource (DataSourceCreate): 数据源创建参数
        db (Session): 数据库会话对象，默认为 Depends(get_sync_session) 获取的同步会话
        user_name (str): 用户名称
        user_id (str): 用户ID
        user_token (str): 用户令牌
    Returns:
        Dict: 包含创建成功的数据源ID的响应
    """
    try:
        if datasource.source_type not in [item.value for item in DataSourceTypeEnum]:
            return response_fail(msg="不支持的数据源类型")
        # user_id = 54
        # 获取数据源连接器
        connector = get_datasource_connector(datasource)
        if not connector.test_connection():
            datasource.source_status = DataSourceStatusEnum.INACTIVE.value
        else:
            if datasource.is_run:
                datasource.source_status = DataSourceStatusEnum.ACTIVE.value
            else:
                datasource.source_status = DataSourceStatusEnum.WAITING.value
        if not user_id:
            return response_fail(msg="用户ID不能为空")
        data_source_id = create_data_source(connector.test_connection(), db, datasource, int(user_id), user_name,
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
    """
    获取数据源列表

    Args:
        user_id (Optional[str]): 用户ID，通过Header传递，默认为None。
        isadmin (Optional[bool]): 是否为管理员，通过Header传递，默认为None。
        page (int): 页码，默认为0。
        pageSize (int): 每页数量，默认为20。
        db (Session): 数据库会话对象，通过Depends注入。

    Returns:
        dict: 包含数据源列表和总记录数的字典。
    """

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
    """
    测试数据源连接。
    Args:
        datasource (DataSourceCreate): 数据源创建对象，包含数据源配置信息。
    Returns:
        dict: 包含测试连接结果的字典。
    """
    try:
        connector = get_datasource_connector(datasource)
        return response_success(data=connector.test_connection())
    except Exception as e:
        logger.error(f"test_datasource_connection: {str(e)}")
        return response_fail(msg=f"测试连接失败:{str(e)}")


@router.put("/datasource/edit/{datasource_id}", response_model=dict)
async def update_datasource(datasource_id: int, datasource: DataSourceUpdate, db: Session = Depends(get_sync_session)):
    try:
        data_source = update_data_source(db, datasource_id, datasource)
        if not data_source:
            return response_fail(msg="更新失败")
        return response_success(data=data_source)
    except Exception as e:
        logger.error(f"update_datasource: {str(e)}")
        return response_fail(msg=f"更新失败:{str(e)}")


@router.delete("/datasource/remove/{datasource_id}", response_model=dict)
async def delete_datasource(datasource_id: int, db: Session = Depends(get_sync_session)):
    """
    更新数据源

    Args:
        datasource_id (int): 数据源ID
        db (Session): 数据库会话对象，默认为 Depends(get_sync_session) 获取的同步会话

    Returns:
        dict: 响应结果，包含操作状态和数据
    """
    try:
        # 判断是否存在执行的任务
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
async def datasource_run_task(datasource_id: int, db: Session = Depends(get_sync_session),
                              user_name: Annotated[str | None, Header(alias="user_name")] = None,
                              user_token: Annotated[str | None, Header(alias="user_token")] = None
                              ):
    """
    执行任务 - 执行新的任务。
    Args:
        datasource_id (int): 数据源ID
        db (Session): 数据库会话对象，通过Depends注入
        user_name (str): 用户名称
        user_token (str): 用户令牌
    Returns:
        dict: 响应结果，包含操作状态和数据
    """
    # 获取数据源信息
    datasource = get_datasource(db, datasource_id)
    if not datasource:
        return response_fail(msg="数据源不存在")
    # 判断是否存在执行的任务
    if has_execting_tasks(db, datasource_id):
        return response_fail(msg="存在执行中的任务，无法执行")
    result, msg = execute_new_collection_task(db, datasource, user_name, user_token)
    if result:
        return response_success(data="任务执行成功")
    return response_fail(msg="任务执行失败:" + msg)


# 表管理+字段API
@router.post("/datasource/tables", response_model=dict)
async def get_datasource_tables(datasource: DataSourceCreate):
    """
    获取数据源中的表列表
    Args:
        datasource: 数据源信息
    """
    try:
        # if datasource.source_type == DataSourceTypeEnum.MONGODB.value:
        #     return response_fail(msg="MongoDB不支持获取表和字段列表")
        # 获取数据源连接器
        connector = get_datasource_connector(datasource)
        if not connector.test_connection():
            return response_fail(msg="数据源连接失败")
        # 查询表列表
        tables = connector.get_tables()
        return response_success(data=tables)
    except Exception as e:
        logger.error(f"获取表列表失败: {str(e)}")
        return response_fail(msg=f"获取表列表失败: {str(e)}")


@router.post("/datasource/table_columns", response_model=dict)
async def get_datasource_table_columns(datasource: DataSourceCreate, table_name: str):
    """
    获取数据源中的表表字段
    Args:
        datasource: 数据源信息
        table_name: 表名称
    """
    try:
        if datasource.source_type == DataSourceTypeEnum.MONGODB.value:
            return response_fail(msg="MongoDB不支持获取表和字段列表")
        # 获取数据源连接器
        connector = get_datasource_connector(datasource)
        if not connector.test_connection():
            return response_fail(msg="数据源连接失败")
        # 查询表字段列表
        columns = connector.get_table_columns(table_name)
        return response_success(data=columns)
    except Exception as e:
        logger.error(f"获取表字段失败: {str(e)}")
        return response_fail(msg=f"获取表字段失败: {str(e)}")
    except Exception as e:
        logger.error(f"获取表字段失败: {str(e)}")
        return response_fail(msg=f"获取字段失败: {str(e)}")


@router.get("/datasource/info", response_model=dict)
async def get_datasource_info(datasource_id: int, db: Session = Depends(get_sync_session)):
    datasource = get_datasource(db, datasource_id)
    task_list, task_total = search_collection_task_all(datasource_id, db)
    return response_success(data={
        'datasourceInfo': datasource.to_json(),
        'task_total': task_total,
        'last_task': task_list[-1].to_dict() if task_list else None,
    })


# 获取表和字段的API
@router.post("/datasource/tables_and_columns", response_model=dict)
async def get_datasource_tables_and_columns(datasource: DataSourceCreate):
    """
    获取数据源中的表及对应字段列表
    Args:
        datasource: 数据源信息
    """
    try:
        if datasource.source_type == DataSourceTypeEnum.MONGODB.value:
            return response_fail(msg="MongoDB不支持获取表和字段列表")
        # 获取数据源连接器（与原方法相同）
        connector = get_datasource_connector(datasource)
        if not connector.test_connection():
            return response_fail(msg="数据源连接失败")
        # 查询表及字段列表（关键差异点：调用获取表和字段的方法）
        tables_and_columns = connector.get_tables_and_columns()  # 假设连接器有此方法
        return response_success(data=tables_and_columns)
    except Exception as e:
        logger.error(f"获取表和字段列表失败: {str(e)}")
        return response_fail(msg=f"获取表和字段列表失败: {str(e)}")


# 采集任务管理API
@router.get("/collectiontasks/list", response_model=dict)
async def collection_task_list(datasource_id: int,
                               page: int = 0, pageSize: int = 20,
                               db: Session = Depends(get_sync_session)):
    """
        获取数据源下的任务列表
        Args:
            datasource_id (int): 数据源id。
            page (int): 页码，默认为0。
            pageSize (int): 每页数量，默认为20。
            db (Session): 数据库会话对象，通过Depends注入。
        Returns:
            dict: 包含数据源列表和总记录数的字典。
        """
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


# 采集任务管理API
@router.get("/collection/task", response_model=dict)
async def get_collection_task_details(task_id: int,
                                      db: Session = Depends(get_sync_session)):
    """
        获取任务信息
        Args:
            task_id (int): 任务ID。
            db (Session): 数据库会话对象，通过Depends注入。
        Returns:
            dict: 获取任务信息。
        """
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
    """
    执行任务 - 执行已存在的任务。
    Args:
        task_id (int): 任务ID
        db (Session): 数据库会话对象，通过Depends注入
        user_name (str): 用户名称
        user_token (str): 用户令牌
    Returns:
        dict: 响应结果，包含操作状态和数据
    """
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
    """
    停止任务 - 停止已存在的任务。
    Args:
        task_id (int): 任务ID
        db (Session): 数据库会话对象，通过Depends注入
    Returns:
        dict: 响应结果，包含操作状态和数据
    """
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
    """
    读取日志 - 读取任务的日志文件。
    Args:
        task_id (int): 任务ID
        db (Session): 数据库会话对象，通过Depends注入
    Returns:
        dict: 响应结果，包含操作状态和数据
    """
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
