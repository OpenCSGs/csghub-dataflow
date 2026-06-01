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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def sqlalchemy_database_uri() -> URL:
    """business_database"""
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
    db_host_name = os.getenv('DATABASE_HOSTNAME', "192.168.2.94")
    db_host_port = os.getenv('DATABASE_PORT', 8198)

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
    """obtain_the_business_database_session"""
    return _SYNC_SESSIONMAKER()


def add_columns_if_missing(table_name: str, columns: dict[str, str]):
    """Add columns to a table if they do not already exist."""
    with get_sync_session() as session:
        with session.begin():
            for column_name, column_sql in columns.items():
                result = session.execute(text(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}' AND column_name = '{column_name}';
                """))
                if not result.fetchone():
                    session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql};"))
                    logger.info(f"Column '{column_name}' added successfully to {table_name} table")


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


def add_mineru_backend_column():
    """Add mineru_backend column to data_format_tasks table"""
    with get_sync_session() as session:
        with session.begin():
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'data_format_tasks' AND column_name = 'mineru_backend';
            """))

            if not result.fetchone():
                session.execute(text("ALTER TABLE data_format_tasks ADD COLUMN mineru_backend VARCHAR(100);"))
                logger.info("Column 'mineru_backend' added successfully to data_format_tasks table")


def add_skip_meta_column():
    """Add skip_meta column to data_format_tasks table"""
    try:
        logger.info("Checking if skip_meta column exists in data_format_tasks table...")
        with get_sync_session() as session:
            with session.begin():
                result = session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'data_format_tasks' AND column_name = 'skip_meta';
                """))

                if not result.fetchone():
                    logger.info("skip_meta column does not exist, adding it...")
                    session.execute(text("ALTER TABLE data_format_tasks ADD COLUMN skip_meta BOOLEAN DEFAULT FALSE;"))
                    logger.info("Column 'skip_meta' added successfully to data_format_tasks table")
                else:
                    logger.info("Column 'skip_meta' already exists in data_format_tasks table")
    except Exception as e:
        logger.error(f"Error adding skip_meta column: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.warning("Continuing despite error...")


def add_csghub_integration_columns():
    add_columns_if_missing("job", {
        "owner_org_id": "VARCHAR(255)",
        "owner_org_name": "VARCHAR(255)",
        "flow_id": "VARCHAR(32)",
        "cluster_id": "VARCHAR(255)",
        "cluster_name": "VARCHAR(255)",
        "resource_id": "INTEGER",
        "resource_name": "VARCHAR(255)",
        "storage_size": "VARCHAR(32)",
        "csghub_job_id": "VARCHAR(100)",
        "csghub_status": "VARCHAR(100)",
        "csghub_request_payload": "TEXT",
        "csghub_response_payload": "TEXT",
        "namespace_uuid": "VARCHAR(255)",
        "namespace_type": "VARCHAR(32)",
    })
    add_columns_if_missing("datasources", {
        "owner_org_id": "VARCHAR(255)",
        "owner_org_name": "VARCHAR(255)",
        "cluster_id": "VARCHAR(255)",
        "cluster_name": "VARCHAR(255)",
        "resource_id": "INTEGER",
        "resource_name": "VARCHAR(255)",
        "storage_size": "VARCHAR(32)",
        "namespace_uuid": "VARCHAR(255)",
        "namespace_type": "VARCHAR(32)",
    })
    add_columns_if_missing("collection_tasks", {
        "flow_id": "VARCHAR(32)",
        "cluster_id": "VARCHAR(255)",
        "cluster_name": "VARCHAR(255)",
        "resource_id": "INTEGER",
        "resource_name": "VARCHAR(255)",
        "storage_size": "VARCHAR(32)",
        "owner_id": "INTEGER",
        "owner_org_id": "VARCHAR(255)",
        "owner_org_name": "VARCHAR(255)",
        "csghub_job_id": "VARCHAR(100)",
        "csghub_status": "VARCHAR(100)",
        "csghub_request_payload": "TEXT",
        "csghub_response_payload": "TEXT",
        "namespace_uuid": "VARCHAR(255)",
        "namespace_type": "VARCHAR(32)",
    })
    add_columns_if_missing("collection_tasks", {
        "is_active": "BOOLEAN DEFAULT TRUE",
        "deleted_at": "TIMESTAMP",
    })
    add_columns_if_missing("data_format_tasks", {
        "is_active": "BOOLEAN DEFAULT TRUE",
        "deleted_at": "TIMESTAMP",
    })
    add_columns_if_missing("data_format_tasks", {
        "owner_org_id": "VARCHAR(255)",
        "owner_org_name": "VARCHAR(255)",
        "flow_id": "VARCHAR(32)",
        "cluster_id": "VARCHAR(255)",
        "cluster_name": "VARCHAR(255)",
        "resource_id": "INTEGER",
        "resource_name": "VARCHAR(255)",
        "storage_size": "VARCHAR(32)",
        "csghub_job_id": "VARCHAR(100)",
        "csghub_status": "VARCHAR(100)",
        "csghub_request_payload": "TEXT",
        "csghub_response_payload": "TEXT",
        "namespace_uuid": "VARCHAR(255)",
        "namespace_type": "VARCHAR(32)",
    })


_initialized = False
from data_server.database.bean.base import Base
from data_server.database.bean.work import Worker
from data_server.job.JobModels import Job
from data_server.job.SubTaskModels import JobSubTask
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

    logger.info("Creating database tables...")
    business_tables = [
        Worker.__table__,
        Job.__table__,
        JobSubTask.__table__,
        DataSource.__table__,
        CollectionTask.__table__,
        DataFormatTask.__table__,
        AlgoTemplate.__table__,
        OperatorInfo.__table__,
        OperatorConfig.__table__,
        OperatorConfigSelectOptions.__table__,
        OperatorPermission.__table__,
    ]
    Base.metadata.create_all(_SYNC_ENGINE, tables=business_tables)
    logger.info("Business tables created successfully")

    _initialized = True

    logger.info("Starting database column migrations...")
    try:
        add_first_op_column()
    except Exception as e:
        logger.error(f"Error in add_first_op_column: {e}")
    
    try:
        add_mineru_api_url_column()
    except Exception as e:
        logger.error(f"Error in add_mineru_api_url_column: {e}")
    
    try:
        add_mineru_backend_column()
    except Exception as e:
        logger.error(f"Error in add_mineru_backend_column: {e}")
    
    try:
        add_skip_meta_column()
    except Exception as e:
        logger.error(f"Error in add_skip_meta_column: {e}")

    try:
        add_csghub_integration_columns()
    except Exception as e:
        logger.error(f"Error in add_csghub_integration_columns: {e}")
    
    logger.info("Database column migrations completed")
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
    # Ensure database schema migrations are applied (check on every startup)
    try:
        add_skip_meta_column()
    except Exception as e:
        logger.warning(f"Could not check/add skip_meta column: {e}")
    
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
        alter_tables_add_description_columns,
        INIT_DATA_VERSION
    )
    
    logger.info(f"Current initialization data version: {INIT_DATA_VERSION}")

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
