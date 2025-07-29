import os,redis
from data_celery.redis_tools.tools import (clear_total_celery_status_from_redis,get_celery_server_list,
                                           del_celery_server_list,set_celery_server_task_count)
def get_radis_database_uri() -> str:
    broker = 'redis://:redis123456@home.sxcfx.cn:18122'
    if os.path.exists(".nat"):
        broker = 'redis://:redis123456@home.sxcfx.cn:18122'
    return broker
def get_redis_client_by_db_number(number: int) -> str:
    redis_url = f'{get_radis_database_uri()}/{number}'
    r = redis.from_url(redis_url, decode_responses=True)
    return r

if __name__ == '__main__':
    # r = get_redis_client_by_db_number(3)
    # # r.set('test', '123456')
    # r.delete('test')
    # value = r.get('test')
    # print(value)
    list_ = get_celery_server_list()
    print(list_)