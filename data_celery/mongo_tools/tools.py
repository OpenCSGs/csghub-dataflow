from data_server.database.session import MONGO_URI
from pymongo import MongoClient
from data_celery.utils import get_timestamp
from enum import Enum
from typing import List, Optional
from data_server.logic.models import OperatorIdentifier, OperatorIdentifierItem
from bson import ObjectId
# mongo 相关

def get_client():
    """
    获取mongodb客户端
    Returns:
        MongoClient: mongodb客户端
    """
    return MongoClient(MONGO_URI)

def get_log_List(
        task_uid: str,
        page: int = 1,
        page_size: int = 10,
        level: str = None,
        type: str = None
):
    if type is None:
        raise "param type is not exist"
    if task_uid is None:
        raise "param task_uid is not exist"
    client = get_client()
    collection = client[type][f"{task_uid}_run_task"]
    # 构建查询条件
    query = {}
    if level:
        query["level"] = level
    # 计算总数
    total_count = collection.count_documents(query)
    # 计算跳过的文档数量
    skip_count = (page - 1) * page_size
    # 执行分页查询
    logs = collection.find(query).skip(skip_count).limit(page_size)
    # 将结果转换为字典列表
    result = [
        {key: str(value) if key == "_id" else value for key, value in log.items()}
        for log in logs
    ]
    client.close()
    # 返回包含分页信息的字典
    return {
        "data": result,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }


def get_pipline_job_log_List(
        task_uid: str,
        page: int = 1,
        page_size: int = 10,
        level: str = None,
        ops_name: str = None
):
    if task_uid is None:
        raise "param task_uid is not exist"
    client = get_client()
    collection = get_pipline_job_collection(client, task_uid)
    # 构建查询条件
    query = {}
    if level and len(level) > 0:
        query["level"] = level
    if ops_name and len(ops_name) > 0:
        query["operator_name"] = ops_name
    # 计算总数
    total_count = collection.count_documents(query)
    # 计算跳过的文档数量
    skip_count = (page - 1) * page_size
    # 执行分页查询
    logs = collection.find(query).skip(skip_count).limit(page_size)
    # 将结果转换为字典列表
    result = [
        {key: str(value) if key == "_id" else value for key, value in log.items()}
        for log in logs
    ]
    client.close()
    # 返回包含分页信息的字典
    return {
        "data": result,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }
class LogLevelEnum(Enum):
    INFO = "info"
    ERROR = "error"
    WARNING = "warning"
    DEBUG = "debug"

def insert_datasource_run_task_log(task_uid: str, content: str, level: str):
    """
    插入数据源运行任务日志
    Args:
        task_uid (str): 任务UID
        content (str): 内容
        level (str): 级别 info error
    """
    client = get_client()
    try:
        collection = get_datasource_collection(client,task_uid)
        log_one = {"level": level, "content": content, "create_at": get_timestamp()}
        collection.insert_one(log_one)
    except Exception as e:
        print(f"mongodb insert datasource run task log failed,error: {e}")
    finally:
        client.close()

def get_datasource_collection(client,task_uid: str):
    """
    获取数据源运行任务对应的collection
    Args:
        client (MongoClient): mongodb客户端
        task_uid (str): 任务UID
    Returns:
        采集任务对应的collection
    """
    return client['datasource'][f"{task_uid}_run_task"]

def insert_datasource_run_task_log_info(task_uid: str, content: str):
    insert_datasource_run_task_log(task_uid=task_uid, content=content, level=LogLevelEnum.INFO.value)


def insert_datasource_run_task_log_error(task_uid: str, content: str):
    insert_datasource_run_task_log(task_uid=task_uid, content=content, level=LogLevelEnum.ERROR.value)



def insert_pipline_job_run_task_log(job_uid: str, content: str, level: str,operator_name: str,operator_index=0):
    if job_uid is None or len(job_uid) == 0:
        return
    client = get_client()
    try:
        collection = get_pipline_job_collection(client,job_uid)
        log_one = {"level": level,"operator_name":operator_name,"operator_index":operator_index, "content": content, "create_at": get_timestamp()}
        collection.insert_one(log_one)
    except Exception as e:
        print(f"mongodb insert pipline run task log failed,error: {e}")
    finally:
        client.close()

def get_pipline_job_collection(client,job_uid: str):
    return client['pipline_job'][f"{job_uid}_run_task"]

def insert_pipline_job_run_task_log_info(job_uid: str, content: str,operator_name: str = "",operator_index: int=0):
    insert_pipline_job_run_task_log(job_uid=job_uid, content=content, level=LogLevelEnum.INFO.value,operator_name=operator_name,operator_index=operator_index)

def insert_pipline_job_run_task_log_error(job_uid: str, content: str,operator_name: str = "",operator_index: int=0):
    insert_pipline_job_run_task_log(job_uid=job_uid, content=content, level=LogLevelEnum.ERROR.value,operator_name=operator_name,operator_index=operator_index)

def insert_pipline_job_run_task_log_warning(job_uid: str, content: str,operator_name: str = "",operator_index: int=0):
    insert_pipline_job_run_task_log(job_uid=job_uid, content=content, level=LogLevelEnum.WARNING.value,operator_name=operator_name,operator_index=operator_index)

def insert_pipline_job_run_task_log_debug(job_uid: str, content: str,operator_name: str = "",operator_index: int=0):
    insert_pipline_job_run_task_log(job_uid=job_uid, content=content, level=LogLevelEnum.DEBUG.value,operator_name=operator_name,operator_index=operator_index)


class OperatorStatusEnum(Enum):
    Waiting = "waiting"
    Processing = "processing"
    SUCCESS = "success"
    ERROR = "error"

def set_pipline_job_operator_status(job_uid: str,status: OperatorStatusEnum, operator_name: str,operator_index=0):
    if job_uid is None or len(job_uid) == 0:
        return
    client = get_client()
    try:
        collection = get_pipline_job_operator_collection(client,job_uid)

        query = {"operator_name": operator_name, "operator_index": operator_index}
        existing_record = collection.find_one(query)
        if existing_record:
            collection.update_one(query, {"$set": {"status": status.value, "end_time": get_timestamp()}})
        else:
            log_one = {"status": status.value,"operator_name":operator_name,"operator_index":operator_index,"start_time": get_timestamp(),"end_time": None}
            collection.insert_one(log_one)
    except Exception as e:
        print(f"mongodb insert pipline run task log failed,error: {e}")
    finally:
        client.close()


def get_pipline_job_operators_status(job_uid: str, operators: List[OperatorIdentifierItem]) -> List[dict]:
    if job_uid is None or len(job_uid) == 0 or not operators:
        return []

    client = get_client()
    try:
        collection = get_pipline_job_operator_collection(client, job_uid)
        operator_names = [operator.name for operator in operators]
        operator_indices = [operator.index for operator in operators]
        query = {
            "operator_name": {"$in": operator_names},
            "operator_index": {"$in": operator_indices}
        }
        results = list(collection.find(query))
        for result in results:
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])

        return results
    except Exception as e:
        print(f"mongodb query pipline job operators status failed, error: {e}")
        return []

    finally:
        client.close()


def get_pipline_job_total_operators_status(job_uid: str) -> List[dict]:
    if job_uid is None or len(job_uid) == 0:
        return []

    client = get_client()
    try:
        collection = get_pipline_job_operator_collection(client, job_uid)
        query = {}
        results = list(collection.find(query))
        for result in results:
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])

        return results
    except Exception as e:
        print(f"mongodb query pipline job operators status failed, error: {e}")
        return []

    finally:
        client.close()

def get_pipline_job_operator_collection(client,job_uid: str):
    return client['pipline_job'][f"{job_uid}_operator_run_task"]


def insert_formatity_task_log(task_uid: str, content: str, level: str):
    client = get_client()
    try:
        collection = get_formatity_collection(client,task_uid)
        log_one = {"level": level, "content": content, "create_at": get_timestamp()}
        collection.insert_one(log_one)
    except Exception as e:
        print(f"mongodb insert formatity task log failed,error: {e}")
    finally:
        client.close()


def get_formatity_collection(client,task_uid: str):
    return client['formatity'][f"{task_uid}_run_task"]

def insert_formatity_task_log_info(task_uid: str,content: str):
    insert_formatity_task_log(task_uid=task_uid,content=content,level=LogLevelEnum.INFO.value)


def insert_formatity_task_log_error(task_uid: str, content: str):
    insert_formatity_task_log(task_uid=task_uid, content=content, level=LogLevelEnum.ERROR.value)
