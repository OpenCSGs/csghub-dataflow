from data_server.database.session import (get_radis_database_uri,get_celery_worker_redis_db,
                                          get_celery_worker_key,get_celery_info_details_key,
                                          get_celery_last_heartbeat_key)
from loguru import logger
import json

def clear_total_celery_status_from_redis() -> None:

    try:
        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_worker_key()
        all_elements = redis_celery.lrange(redis_key, 0, -1)
        key_list = [str(key) for key in all_elements]
        for worker_name in key_list:
            celery_info_details_key = get_celery_info_details_key(worker_name)
            redis_celery.delete(celery_info_details_key)
            # Simultaneously delete the backed-up heart rate time data
            last_heartbeat_key = get_celery_last_heartbeat_key(worker_name)
            redis_celery.delete(last_heartbeat_key)
        redis_celery.delete(redis_key)
    except Exception as e:
        logger.error(f"clear_total_celery_status_from_redis 执行出错: {e}")

def get_celery_server_list():

    try:
        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_worker_key()
        all_elements = redis_celery.lrange(redis_key, 0, -1)
        return [str(element) for element in all_elements]
    except Exception as e:
        logger.error(f"celery_server_list 执行出错: {e}")

def del_celery_server_list(worker_name):

    try:
        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_worker_key()
        redis_celery.lrem(redis_key, 0, worker_name)
    except Exception as e:
        logger.error(f"del_celery_server_list 执行出错: {e}")

def set_celery_server_status(worker_name,status_json,expire_sec=None):

    try:
        redis_celery = get_celery_worker_redis_db()
        celery_info_details_key = get_celery_info_details_key(worker_name)
        redis_celery.set(celery_info_details_key, status_json, expire_sec)
        logger.info(f"set_celery_server_status 设置了worker:{celery_info_details_key},状态: {status_json}")
        # Simultaneously save the last heartbeat time to the backup key (no expiration time is set, permanently saved)
        try:
            dict_result = json.loads(status_json)
            if "current_time" in dict_result:
                last_heartbeat_key = get_celery_last_heartbeat_key(worker_name)
                heartbeat_data = {
                    "current_time": dict_result["current_time"],
                    "current_ip": dict_result.get("current_ip", "")
                }
                # The backup data does not have an expiration time set and is permanently saved (until the worker is deleted)
                redis_celery.set(last_heartbeat_key, json.dumps(heartbeat_data))
        except Exception as backup_error:
            logger.warning(f"保存最后一次心跳时间备份失败: {backup_error}")
    except Exception as e:
        logger.error(f"set_celery_server_status 执行出错: {e}")

def get_celery_last_heartbeat(worker_name):

    try:
        redis_celery = get_celery_worker_redis_db()
        last_heartbeat_key = get_celery_last_heartbeat_key(worker_name)
        result = redis_celery.get(last_heartbeat_key)
        if result:
            return json.loads(result)
        return None
    except Exception as e:
        logger.error(f"get_celery_last_heartbeat fail: {e}")
        return None

def celery_server_status_is_exists(worker_name):

    try:
        redis_celery = get_celery_worker_redis_db()
        celery_info_details_key = get_celery_info_details_key(worker_name)
        return redis_celery.exists(celery_info_details_key)
    except Exception as e:
        logger.error(f"celery_server_status_is_exists 执行出错: {e}")


def add_celery_server_to_list(worker_name):

    try:
        redis_celery = get_celery_worker_redis_db()
        redis_key = get_celery_worker_key()
        all_elements = redis_celery.lrange(redis_key, 0, -1)
        real_key = worker_name
        if real_key not in [str(element) for element in all_elements]:
            redis_celery.rpush(redis_key, real_key)
    except Exception as e:
        logger.error(f"add_celery_server_to_list 执行出错: {e}")
