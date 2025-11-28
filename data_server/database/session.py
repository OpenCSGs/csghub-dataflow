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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def sqlalchemy_database_uri() -> URL:
    db_user_name = ""
    db_user_pwd = ""
    db_host_name = ""
    db_host_port = 5432

    # db_user_name = os.getenv('DATABASE_USERNAME', "admin")
    # db_user_pwd = os.getenv('DATABASE_PASSWORD', "admin123456")
    # db_host_name = os.getenv('DATABASE_HOSTNAME', "net-power.9free.com.cn")
    # db_host_port = os.getenv('DATABASE_PORT', 18119)

    db_user_name = os.getenv('DATABASE_USERNAME', "postgres")
    db_user_pwd = os.getenv('DATABASE_PASSWORD', "postgres")
    db_host_name = os.getenv('DATABASE_HOSTNAME', "127.0.0.1")
    db_host_port = os.getenv('DATABASE_PORT', 5433)

    db_name = os.getenv('DATABASE_DB', "data_flow")
    print(f"connect to {db_user_name}:{db_user_pwd}@{db_host_name}:{db_host_port}/{db_name}")
    return URL.create(
        # drivername="postgresql+asyncpg",
        drivername="postgresql",
        username=db_user_name,
        password=db_user_pwd,
        host=db_host_name,
        port=db_host_port,
        database=db_name
    )


def get_radis_database_uri() -> str:
    return os.getenv("REDIS_HOST_URL", "redis://192.168.2.10:6379")


def get_redis_client_by_db_number(number: int) -> str:
    redis_url = f'{get_radis_database_uri()}/{number}'
    r = redis.from_url(redis_url, decode_responses=True)
    return r


def get_celery_worker_redis_db():

    return get_redis_client_by_db_number(5)


def get_celery_worker_key():

    return 'celery-worker-server-list'

def get_celery_process_list_key(work_name,current_ip):

    return f"{work_name}_{current_ip}_processes"


def get_celery_kill_process_list_key(work_name,current_ip):

    return f"{work_name}_{current_ip}_kill_processes"



def get_celery_task_process_real_key(task_uid):

    return f"celery-pipline-task:{task_uid}"

def get_celery_task_process_resource_key(task_uid):
    return f"celery-pipline-task-resource:{task_uid}"

def get_celery_info_details_key(work_name):

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



MONGO_URI = os.getenv('MONG_HOST_URL', 'mongodb://root:example@net-power.9free.com.cn:10002')


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


def add_mineru_api_url_column():
    """Add mineru_api_url column to data_format_tasks table"""
    with get_sync_session() as session:
        with session.begin():
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'data_format_tasks' AND column_name = 'mineru_api_url';
            """))

            if not result.fetchone():
                session.execute(text("ALTER TABLE data_format_tasks ADD COLUMN mineru_api_url VARCHAR(500);"))
                logger.info("Column 'mineru_api_url' added successfully to data_format_tasks table")


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
    add_mineru_api_url_column()
def is_table_initialized(table_name: str) -> bool:
    """
    Check if a specific table contains any data.
    """
    with get_sync_session() as session:
        try:
            result = session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.warning(f"Could not check table '{table_name}', assuming it's not initialized. Error: {e}")
            return False

def initialize_database():
    """
    Selectively initializes tables if they are empty.
    Automatically executes one-time deletion on first startup (tracked in deletion_status table).
    This should be called once when the application starts.
    """
    tables_to_initialize = [
        'operator_info',
        'operator_config',
        'operator_config_select_options',
        'algo_templates'
    ]

    logger.info("Starting selective database data initialization check...")
    from .initializer import (
        initialize_table,
        delete_table_data_by_ids,
        has_deletion_been_executed,
        mark_deletion_as_executed,
        has_table_alteration_been_executed,
        mark_table_alteration_as_executed,
        alter_tables_add_description_columns
    )

    should_alter_tables = not has_table_alteration_been_executed()
    should_delete = not has_deletion_been_executed()

    if should_alter_tables:
        logger.info("First time startup detected, executing one-time table alteration...")
        try:
            alter_tables_add_description_columns()
            mark_table_alteration_as_executed()
            logger.info("Table alteration completed and marked as executed.")
        except Exception as e:
            logger.error(f"Error during table alteration process: {e}")
            logger.warning("Table alteration interrupted, but will continue...")

    if should_delete:
        logger.info("First time startup detected, executing one-time deletion...")
        try:
            for table in tables_to_initialize:
                delete_table_data_by_ids(table)
            mark_deletion_as_executed()
            logger.info("Data deletion completed and marked as executed.")
        except Exception as e:
            logger.error(f"Error during deletion process: {e}")
            logger.warning("Deletion process interrupted, but will continue with initialization...")

        logger.info("Force re-initializing all tables after deletion...")
        for table in tables_to_initialize:
            logger.info(f"Force initializing table '{table}'...")
            try:
                initialize_table(table)
            except Exception as e:
                logger.error(f"Error initializing table '{table}': {e}")
                logger.warning(f"Continuing with next table...")
    else:
        logger.info("Deletion already executed on previous startup, skipping...")

        for table in tables_to_initialize:
            if is_table_initialized(table):
                logger.info(f"Table '{table}' already contains data, skipping initialization.")
                # Update sequence even when skipping initialization to avoid conflicts
                from .initializer import update_sequence_for_table
                update_sequence_for_table(table)
            else:
                logger.info(f"Table '{table}' is empty, proceeding with initialization.")
                initialize_table(table)

    logger.info("Database selective initialization process completed.")


create_tables()
