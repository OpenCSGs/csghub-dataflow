from data_celery.main import celery_app
from data_celery.test01.tasks import test_01, test_02
import time
from data_server.datasource.DatasourceTask import stop_celery_task

if __name__ == '__main__':
    stop_celery_task("38a5de31-ea19-4bcb-a4ef-b4495edc1bfb")
    stop_celery_task("665f713d-e4a7-4cc4-b6e9-cf160c7afcf8")
    stop_celery_task("29baea0c-9ac8-4c5d-bc04-b66a3ec7d0c0")
    '''
    任务1 ID: 38a5de31-ea19-4bcb-a4ef-b4495edc1bfb
    任务2 ID: 665f713d-e4a7-4cc4-b6e9-cf160c7afcf8
    任务3 ID: 29baea0c-9ac8-4c5d-bc04-b66a3ec7d0c0
    
    '''
