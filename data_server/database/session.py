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

def sqlalchemy_database_uri() -> URL:
    return URL.create(
        # drivername="postgresql+asyncpg",
        drivername="postgresql",
        username=os.getenv('DATABASE_USERNAME', "postgres"),
        password=os.getenv('DATABASE_PASSWORD',"postgres"),
        host=os.getenv('DATABASE_HOSTNAME',"localhost"),
        port=os.getenv('DATABASE_PORT',5432),
        database=os.getenv('DATABASE_DB',"data_flow")
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
   )
    
_SYNC_ENGINE = create_sync_engine(sqlalchemy_database_uri())
_SYNC_SESSIONMAKER = sessionmaker(_SYNC_ENGINE, expire_on_commit=False)
def get_sync_session() -> Session:  # pragma: no cover
    return _SYNC_SESSIONMAKER()

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
def create_tables():
    global _initialized
    if _initialized:
        return
    Worker.metadata.create_all(_SYNC_ENGINE)
    Job.metadata.create_all(_SYNC_ENGINE)
    _initialized = True

    add_first_op_column()

create_tables()