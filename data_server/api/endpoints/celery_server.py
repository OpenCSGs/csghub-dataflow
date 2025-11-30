import json

from fastapi import FastAPI, APIRouter, HTTPException, status, Header, Depends
from sqlalchemy.orm import Session
from typing import Annotated, Union
from loguru import logger
from data_server.database.session import get_sync_session
from data_server.schemas.responses import response_success, response_fail
from data_celery.redis_tools.tools import get_celery_server_list, del_celery_server_list
from data_server.database.session import get_celery_worker_redis_db,get_celery_info_details_key
from data_celery.utils import get_timestamp

router = APIRouter()


@router.get("/get_celery_server_list", response_model=dict)
async def get_celery_server_list_api(isadmin: Annotated[bool | None, Header(alias="isadmin")] = None):

    try:
        # if isadmin is None or isadmin == False:


        server_list = get_celery_server_list()
        ret_list = []
        celery_redis = get_celery_worker_redis_db()
        pipe = celery_redis.pipeline()

        for key in server_list:
            logger.info(f"get_celery_info_details_key: {get_celery_info_details_key(key)}")
            pipe.get(get_celery_info_details_key(key))

        results = pipe.execute()
        worker_name_dict = {}
        for result in results:
            if result is not None:
                dict_result = json.loads(result)
                if "worker_name" in dict_result:
                    worker_name_dict[dict_result["worker_name"]] = dict_result
        for server_key in server_list:
            if server_key in worker_name_dict:
                dict_result = worker_name_dict[server_key]
                if "current_time" in dict_result:
                    current_time = dict_result["current_time"]
                    if get_timestamp() - current_time > 12:
                        ret_list.append(
                            {'worker_name': server_key, 'task_count': 0, 'current_ip': "", "status": "offline", "ack_time": current_time})
                    else:
                        ret_list.append({'worker_name': server_key, 'task_count': dict_result['task_count'],
                                         'current_ip': dict_result['current_ip'], "status": "online", "ack_time": current_time})
            else:
                ret_list.append({'worker_name': server_key, 'task_count': 0, 'current_ip': "", "status": "offline", "ack_time": 0})

        return response_success(data=ret_list)
    except Exception as e:
        logger.error(f"get_celery_server_list 执行出错: {e}")
        return response_fail(msg="获取Celery服务器列表失败")


@router.delete("/delete_celery_worker/{worker_name}", response_model=dict)
async def delete_celery_worker_api(worker_name: str, isadmin: Annotated[bool | None, Header(alias="isadmin")] = None):
    try:
        if isadmin is None or isadmin == False:
            return response_fail(msg="Only the admin can delete the Worker")

        worker_name = worker_name.strip()

        server_list = get_celery_server_list()
        if worker_name not in server_list:
            return response_fail(msg=f"Worker '{worker_name}' it_doesn_t_exist")

        del_celery_server_list(worker_name)

        celery_redis = get_celery_worker_redis_db()
        celery_info_details_key = get_celery_info_details_key(worker_name)
        celery_redis.delete(celery_info_details_key)

        logger.info(f"the_administrator_manually_deletes_the_worker: {worker_name}")
        return response_success(msg=f"successfully_deleted_worker: {worker_name}")
    except Exception as e:
        logger.error(f"delete_celery_worker error: {e}")
        return response_fail(msg=f"failed_to_delete_the_worker: {str(e)}")

