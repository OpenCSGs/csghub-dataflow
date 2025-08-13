from data_celery.main import celery_app
from data_celery.test01.tasks import test_01, test_02
import time
from datetime import datetime
import pytz
if __name__ == '__main__':
    # print("main")
    # # 保存任务结果对象
    # result2 = test_02.delay("c2")
    #
    # print(f"任务2 ID: {result2.id}")
    #
    # print("main end")
    #
    # # 可选：检查任务状态（不推荐立即检查，仅用于调试）
    # time.sleep(1)
    # print(f"任务2状态: {result2.status}")

    #
    # result1 = test_01.delay("任务1---")
    #
    # print(f"任务1 ID: {result1.id}")
    #
    # result2 = test_01.delay("任务2---")
    #
    # print(f"任务2 ID: {result2.id}")
    #
    # result3 = test_01.delay("任务3---")
    #
    # print(f"任务3 ID: {result3.id}")

    # 使用带时区的时间
    # shanghai_tz = pytz.timezone('Asia/Shanghai')
    # eta_time = shanghai_tz.localize(datetime(2025, 8, 1, 11, 31, 0))
    # task_celery = test_01.apply_async(args=['11点31任务'], eta=eta_time)
    #
    # '''
    # 任务1 ID: 38a5de31-ea19-4bcb-a4ef-b4495edc1bfb
    # 任务2 ID: 665f713d-e4a7-4cc4-b6e9-cf160c7afcf8
    # 任务3 ID: 29baea0c-9ac8-4c5d-bc04-b66a3ec7d0c0
    # '''
    # result1 = test_01.delay("c1....")

    # print(f"任务1 ID: {result1.id}")

    # afdaadcf-0fb3-4055-9440-cc058a06196b
    inspector = celery_app.control.inspect()

    active_tasks = inspector.active()
    if active_tasks:
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                print(f"Worker Name: {worker_name}, Task ID: {task['id']}")
    else:
        print("No active tasks found.")