from data_celery.main import celery_app
from loguru import logger
import time

@celery_app.task(name="test_01")
def test_01(name):
    for i in range(1000):
        logger.info(f"test:{name} 开启执行")
        time.sleep(10)
    logger.info(f"test:{name} 执行结束")
    return True


@celery_app.task(name="test_02")
def test_02(name):
    for i in range(1000):
        logger.info(f"test:{name} 开启执行")
        time.sleep(10)
    logger.info(f"test_02:{name} 执行结束")
    return True