from data_celery.main import celery_app
from data_celery.test01.tasks import test_01, test_02
import time
from datetime import datetime
import pytz
if __name__ == '__main__':
    # print("main")

    # result2 = test_02.delay("c2")
    #

    #
    # print("main end")
    #

    # time.sleep(1)


    #

    #

    #

    #

    #

    #



    # shanghai_tz = pytz.timezone('Asia/Shanghai')
    # eta_time = shanghai_tz.localize(datetime(2025, 8, 1, 11, 31, 0))

    #
    # '''

    # '''
    # result1 = test_01.delay("c1....")



    # afdaadcf-0fb3-4055-9440-cc058a06196b
    inspector = celery_app.control.inspect()

    active_tasks = inspector.active()
    if active_tasks:
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                print(f"Worker Name: {worker_name}, Task ID: {task['id']}")
    else:
        print("No active tasks found.")