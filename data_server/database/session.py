# SQLAlchemy async engine and sessions tools
#
# https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
#
# for pool size configuration:
# https://docs.sqlalchemy.org/en/20/core/pooling.html#sqlalchemy.pool.Pool

from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from collections.abc import AsyncGenerator
import os
from loguru import logger
import redis


def sqlalchemy_database_uri() -> URL:
    return URL.create(
        # drivername="postgresql+asyncpg",
        drivername="postgresql",
        username=os.getenv('DATABASE_USERNAME', "admin"),
        password=os.getenv('DATABASE_PASSWORD', "admin123456"),
        host=os.getenv('DATABASE_HOSTNAME', "net-power.9free.com.cn"),
        port=os.getenv('DATABASE_PORT', 18119),
        database=os.getenv('DATABASE_DB', "data_flow")
    )


def get_radis_database_uri() -> str:
    # return os.getenv("REDIS_HOST_URL", "redis://:redis123456@net-power.9free.com.cn:18122")
    return os.getenv("REDIS_HOST_URL", "redis://127.0.0.1:6379")


def get_redis_client_by_db_number(number: int) -> str:
    redis_url = f'{get_radis_database_uri()}/{number}'
    r = redis.from_url(redis_url, decode_responses=True)
    return r


def get_celery_worker_redis_db():
    """
    获取Celery工作进程的Redis数据库连接。

    Returns:
        返回连接到Redis数据库（数据库编号为5）的客户端对象。
    """
    return get_redis_client_by_db_number(5)


def get_celery_worker_key():
    """
    获取Celery工作进程的Redis worker list key。

    Returns:
        返回字符串，表示Celery工作进程使用的Redis worker list key。
    """
    return 'celery-worker-server-list'

def get_celery_process_list_key(work_name,current_ip):
    """
    获取Celery工作进程的Redis process list key。
    Args:
        work_name: 工作名称
        current_ip: 当前IP地址

    Returns:
        返回字符串，表示Celery工作进程使用的Redis process list key。
    """
    return f"{work_name}_{current_ip}_processes"


def get_celery_kill_process_list_key(work_name,current_ip):
    """
    获取Celery工作进程的Redis kill process list key。
    Args:
        work_name: 工作名称
        current_ip: 当前IP地址

    Returns:
        返回字符串，表示Celery工作进程使用的Redis kill process list key。
    """
    return f"{work_name}_{current_ip}_kill_processes"



def get_celery_task_process_real_key(task_uid):
    """
    获取Celery任务详细信息的Redis key。

    Returns:
        返回字符串，表示Celery任务详细信息的Redis key。
    """
    return f"celery-pipline-task:{task_uid}"

def get_celery_task_process_resource_key(task_uid):
    return f"celery-pipline-task-resource:{task_uid}"

def get_celery_info_details_key(work_name):
    """
    获取Celery任务详细信息的Redis key。

    Returns:
        返回字符串，表示Celery任务详细信息的Redis key。
    """
    return f'celery-worker-time:{work_name}'


# def new_async_engine(uri: URL) -> AsyncEngine:
#     return create_async_engine(
#         uri,
#         pool_pre_ping=True,
#         pool_size=5,
#         max_overflow=10,
#         pool_timeout=30.0,
#         pool_recycle=600,
#     )

# def get_async_session() -> AsyncSession:  # pragma: no cover
#     return _ASYNC_SESSIONMAKER()

# async def get_session() -> AsyncGenerator[AsyncSession, None]:
#     async with get_async_session() as session:
#         yield session

# _ASYNC_ENGINE = new_async_engine(sqlalchemy_database_uri())
# _ASYNC_SESSIONMAKER = async_sessionmaker(_ASYNC_ENGINE, expire_on_commit=False)


def create_sync_engine(uri: URL) -> Engine:
    return create_engine(
        uri,
        pool_pre_ping=True,
        pool_size=50,
        max_overflow=100,
        pool_timeout=30.0,
        pool_recycle=600,
        # echo=True
    )


_SYNC_ENGINE = create_sync_engine(sqlalchemy_database_uri())
_SYNC_SESSIONMAKER = sessionmaker(_SYNC_ENGINE, expire_on_commit=False)


def get_sync_session() -> Session:  # pragma: no cover
    return _SYNC_SESSIONMAKER()


# MONG 相关
MONGO_URI = os.getenv('MONG_HOST_URL', 'mongodb://root:example@net-power.9free.com.cn:18123')


def add_first_op_column():
    with get_sync_session() as session:
        with session.begin():
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'job' AND column_name = 'first_op';
            """))

            if not result.fetchone():
                session.execute(text("ALTER TABLE job ADD COLUMN first_op VARCHAR;"))
                session.execute(text("UPDATE job SET first_op = '' WHERE first_op IS NULL;"))
                logger.info("Column 'first_op' added successfully")


_initialized = False
from data_server.database.bean.work import Worker
from data_server.job.JobModels import Job
from data_server.datasource.DatasourceModels import DataSource, CollectionTask
from data_server.formatify.FormatifyModels import DataFormatTask
from data_server.algo_templates.model.algo_template import AlgoTemplate
from data_server.operator.models.operator import OperatorInfo,OperatorConfig,OperatorConfigSelectOptions
from data_server.operator.models.operator_permission import OperatorPermission


def create_tables():
    global _initialized
    if _initialized:
        return
    
    logger.info("Starting database table creation...")
    Worker.metadata.create_all(_SYNC_ENGINE)
    Job.metadata.create_all(_SYNC_ENGINE)
    DataSource.metadata.create_all(_SYNC_ENGINE)
    CollectionTask.metadata.create_all(_SYNC_ENGINE)
    DataFormatTask.metadata.create_all(_SYNC_ENGINE)
    AlgoTemplate.metadata.create_all(_SYNC_ENGINE)
    OperatorInfo.metadata.create_all(_SYNC_ENGINE)
    OperatorConfig.metadata.create_all(_SYNC_ENGINE)
    OperatorConfigSelectOptions.metadata.create_all(_SYNC_ENGINE)
    OperatorPermission.metadata.create_all(_SYNC_ENGINE)
    logger.info("Database tables created successfully")

    _initialized = True

    add_first_op_column()

    # Execute the data initialization script
    logger.info("Starting database data initialization...")
    from .initializer import execute_initialization_scripts
    execute_initialization_scripts()
    logger.info("Database initialization process completed")


create_tables()
