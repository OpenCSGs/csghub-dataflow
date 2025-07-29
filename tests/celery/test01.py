from data_celery.main import celery_app
from data_celery.test01.tasks import test_01, test_02
import time

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


    result1 = test_01.delay("任务1---")

    print(f"任务1 ID: {result1.id}")

    result2 = test_01.delay("任务2---")

    print(f"任务2 ID: {result2.id}")

    result3 = test_01.delay("任务3---")

    print(f"任务3 ID: {result3.id}")

    '''
    任务1 ID: 38a5de31-ea19-4bcb-a4ef-b4495edc1bfb
    任务2 ID: 665f713d-e4a7-4cc4-b6e9-cf160c7afcf8
    任务3 ID: 29baea0c-9ac8-4c5d-bc04-b66a3ec7d0c0
    
    '''
