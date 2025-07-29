from data_server.database.session import MONGO_URI
from pymongo import MongoClient
from data_celery.utils import get_timestamp


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
    insert_datasource_run_task_log(task_uid=task_uid, content=content, level="info")


def insert_datasource_run_task_log_error(task_uid: str, content: str):
    insert_datasource_run_task_log(task_uid=task_uid, content=content, level="error")


def insert_formatity_task_log(task_uid: str, content: str, level: str):
    """
    插入格式化任务日志
    Args:
        task_uid (str): 任务UID
        content (str): 内容
        level (str): 级别 info error
    """
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
    """
    获取格式转换任务对应的collection
    Args:
        client (MongoClient): mongodb客户端
        task_uid (str): 任务UID
    Returns:
        任务对应的collection
    """
    return client['formatity'][f"{task_uid}_task"]

def insert_formatity_task_log_info(task_uid: str,content: str):
    insert_formatity_task_log(task_uid=task_uid,content=content,level="info")

def insert_formatity_task_log_info(task_uid: str, content: str):
    insert_formatity_task_log(task_uid=task_uid, content=content, level="info")


def insert_formatity_task_log_error(task_uid: str, content: str):
    insert_formatity_task_log(task_uid=task_uid, content=content, level="error")

# def get_pipline_job_mongo_collection(job_uuid: str,job_type: str) -> str:
#     """
#     获取pipline任务对应的collection
#     Args:
#         job_uuid (str): 任务UID
#         job_type (str): 任务类型
#     Returns:
#         str: 采集任务对应的collection
#     """
#     return get_mongo_db("datasource")[f"{job_type}_{job_uuid}_task"]