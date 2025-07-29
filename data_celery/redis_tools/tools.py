from data_server.database.session import (get_radis_database_uri,get_celery_worker_redis_db,
                                          get_celery_worker_key,get_celery_info_details_key)
from loguru import logger

def clear_total_celery_status_from_redis() -> None:
    """
    如果celery没有启动的服务，直接全部清除
    """
    try:
        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_worker_key()
        all_elements = redis_celery.lrange(redis_key, 0, -1)  # 0 到 -1 表示所有元素
        key_list = [str(key) for key in all_elements]
        for worker_name in key_list:
            celery_info_details_key = get_celery_info_details_key(worker_name)
            redis_celery.delete(celery_info_details_key)
        redis_celery.delete(redis_key)
    except Exception as e:
        logger.error(f"clear_total_celery_status_from_redis 执行出错: {e}")

def get_celery_server_list():
    """
    celery服务列表
    """
    try:
        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_worker_key()
        all_elements = redis_celery.lrange(redis_key, 0, -1)  # 0 到 -1 表示所有元素
        return [str(element) for element in all_elements]
    except Exception as e:
        logger.error(f"celery_server_list 执行出错: {e}")

def del_celery_server_list(worker_name):
    """
    删除celery服务
    """
    try:
        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_worker_key()
        redis_celery.lrem(redis_key, 0, worker_name)
    except Exception as e:
        logger.error(f"del_celery_server_list 执行出错: {e}")

def set_celery_server_status(worker_name,status_json,expire_sec=None):
    """
    设置celery服务状态
    """
    try:
        redis_celery = get_celery_worker_redis_db()
        celery_info_details_key = get_celery_info_details_key(worker_name)
        redis_celery.set(celery_info_details_key, status_json, expire_sec)
    except Exception as e:
        logger.error(f"set_celery_server_status 执行出错: {e}")

def celery_server_status_is_exists(worker_name):
    """
    判断celery服务是否存在
    """
    try:
        redis_celery = get_celery_worker_redis_db()
        celery_info_details_key = get_celery_info_details_key(worker_name)
        return redis_celery.exists(celery_info_details_key)
    except Exception as e:
        logger.error(f"celery_server_status_is_exists 执行出错: {e}")


def add_celery_server_to_list(worker_name):
    """
    添加celery服务到列表
    """
    try:
        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_worker_key()
        all_elements = redis_celery.lrange(redis_key, 0, -1)  # 0 到 -1 表示所有元素
        real_key = worker_name
        if real_key not in [str(element) for element in all_elements]:
            redis_celery.rpush(redis_key, real_key)
    except Exception as e:
        logger.error(f"add_celery_server_to_list 执行出错: {e}")
