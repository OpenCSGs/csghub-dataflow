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
from sqlalchemy import create_engine, Engine, text, inspect
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


def _sqlalchemy_type_to_sql(col_type) -> str:
    """Convert a SQLAlchemy Column type to a SQL DDL type string."""
    from sqlalchemy import (
        Integer, BigInteger, SmallInteger,
        String, Text, Unicode, UnicodeText,
        Boolean,
        DateTime, Date, Time,
        Float, Numeric,
        JSON,
    )
    from sqlalchemy.dialects.postgresql import JSONB

    type_map = {
        Integer: "INTEGER",
        BigInteger: "BIGINT",
        SmallInteger: "SMALLINT",
        String: "VARCHAR",
        Text: "TEXT",
        Unicode: "VARCHAR",
        UnicodeText: "TEXT",
        Boolean: "BOOLEAN",
        DateTime: "TIMESTAMP",
        Date: "DATE",
        Time: "TIME",
        Float: "FLOAT",
        Numeric: "NUMERIC",
        JSON: "JSON",
        JSONB: "JSONB",
    }

    for py_type, sql_name in type_map.items():
        if isinstance(col_type, py_type):
            if isinstance(col_type, String) and col_type.length:
                return f"VARCHAR({col_type.length})"
            return sql_name

    return str(col_type).upper()


def sync_missing_columns_for_tables(table_models: list):
    """
    自动检测所有 ORM 模型中定义的字段，与数据库实际字段对比，
    对于数据库中缺失的字段，自动执行 ALTER TABLE ADD COLUMN 补齐。

    这覆盖了未来任意模型字段新增的场景，不再需要为每个新字段硬编码
    单独的 add_xxx_column() 函数。每个表单独提交事务，失败不影响其他表。
    """
    inspector = inspect(_SYNC_ENGINE)

    for table in table_models:
        table_name = table.name
        try:
            db_columns = {col["name"] for col in inspector.get_columns(table_name)}
        except Exception:
            logger.debug(f"Table '{table_name}' does not exist yet, skipping column sync")
            continue

        model_columns = {col.name: col for col in table.columns}

        for col_name, col in model_columns.items():
            if col_name not in db_columns:
                col_type_sql = _sqlalchemy_type_to_sql(col.type)
                nullable = "" if col.nullable else " NOT NULL"
                default_clause = ""
                if col.default is not None:
                    default_val = col.default.arg
                    if isinstance(default_val, bool):
                        default_clause = f" DEFAULT {'TRUE' if default_val else 'FALSE'}"
                    elif isinstance(default_val, (int, float)):
                        default_clause = f" DEFAULT {default_val}"
                    elif isinstance(default_val, str):
                        default_clause = f" DEFAULT '{default_val}'"

                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type_sql}{default_clause}{nullable}"
                logger.info(f"Detected missing column: {table_name}.{col_name} -> executing: {alter_sql}")

                with get_sync_session() as session:
                    try:
                        session.execute(text(alter_sql))
                        session.commit()
                        logger.info(f"Column '{table_name}.{col_name}' added successfully")
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Failed to add column '{table_name}.{col_name}': {e}")


def drop_obsolete_columns():
    """
    删除 ORM 模型中已不存在、但数据库中仍然残留的废弃字段。

    本次 Argo 迁移移除的字段：
      - job: job_celery_uuid, job_celery_work_name
      - collection_tasks: task_celery_uid
      - data_format_tasks: task_celery_uid

    使用 DROP COLUMN IF EXISTS，重复执行安全。
    """
    obsolete_columns = {
        "job": ["job_celery_uuid", "job_celery_work_name"],
        "collection_tasks": ["task_celery_uid"],
        "data_format_tasks": ["task_celery_uid"],
    }

    logger.info("Checking for obsolete columns to drop...")
    with get_sync_session() as session:
        for table_name, columns in obsolete_columns.items():
            for col_name in columns:
                try:
                    session.execute(text(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_name}"))
                    session.commit()
                    logger.info(f"Dropped obsolete column '{table_name}.{col_name}' (if existed)")
                except Exception as e:
                    session.rollback()
                    logger.warning(f"Could not drop obsolete column '{table_name}.{col_name}': {e}")


def auto_drop_obsolete_columns(table_models: list):
    """
    自动对比数据库实际列与 ORM 模型定义的列，删除数据库中多余（ORM 已不再定义）的列。

    使用 SQLAlchemy Inspector 获取数据库实际列清单，与 ORM 模型的 table.columns 对比，
    对 ORM 中不存在的列执行 DROP COLUMN IF EXISTS。
    每个表单独提交事务，失败不影响其他表。
    """
    inspector = inspect(_SYNC_ENGINE)

    for table in table_models:
        table_name = table.name
        try:
            db_columns = {col["name"] for col in inspector.get_columns(table_name)}
        except Exception:
            logger.debug(f"Table '{table_name}' does not exist yet, skipping obsolete column check")
            continue

        model_columns = {col.name for col in table.columns}

        for col_name in db_columns - model_columns:
            logger.info(f"Detected obsolete column: {table_name}.{col_name} -> dropping...")
            with get_sync_session() as session:
                try:
                    session.execute(text(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_name}"))
                    session.commit()
                    logger.info(f"Dropped obsolete column '{table_name}.{col_name}'")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to drop obsolete column '{table_name}.{col_name}': {e}")


# ============================================================
#  Schema Version Management
# ============================================================

SCHEMA_VERSION = "1.0.4"


def _version_to_tuple(v: str) -> tuple:
    """将版本号字符串转为可比较的元组，如 '1.0.10' -> (1, 0, 10)。"""
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)


def _ensure_version_tracking_table():
    """确保 deletion_status 表存在且结构正确（有主键自增 id）。"""
    try:
        with get_sync_session() as session:
            # Step 1: 创建表（不存在时）
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS deletion_status (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(50),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
                )
            """))
            session.commit()

            # Step 2: 修复已有表缺少 id 列的情况
            result = session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'deletion_status' AND column_name = 'id'
            """))
            if result.fetchone() is None:
                logger.info("Adding id column to existing deletion_status table...")
                session.execute(text("ALTER TABLE deletion_status ADD COLUMN id SERIAL"))
                session.commit()

            # Step 3: 确保 id 列有 PRIMARY KEY 约束
            result = session.execute(text("""
                SELECT kc.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kc ON tc.constraint_name = kc.constraint_name
                WHERE tc.table_name = 'deletion_status' AND tc.constraint_type = 'PRIMARY KEY'
            """))
            pk_columns = [row[0] for row in result.fetchall()]
            if 'id' not in pk_columns:
                logger.info("Adding PRIMARY KEY on id column...")
                session.execute(text("ALTER TABLE deletion_status ADD PRIMARY KEY (id)"))
                session.commit()

            # Step 4: 确保 id 有对应的 SEQUENCE，支持自动递增
            seq_name = "deletion_status_id_seq"
            result = session.execute(text(f"""
                SELECT sequence_name FROM information_schema.sequences
                WHERE sequence_name = '{seq_name}'
            """))
            if result.fetchone() is None:
                logger.info(f"Creating sequence {seq_name} for auto-increment...")
                session.execute(text(f"CREATE SEQUENCE {seq_name}"))
                session.execute(text(f"ALTER SEQUENCE {seq_name} OWNED BY deletion_status.id"))
                session.commit()
            else:
                session.execute(text(f"ALTER SEQUENCE {seq_name} OWNED BY deletion_status.id"))
                session.commit()

            # Step 5: 设置 id 默认值从序列取值
            session.execute(text(f"""
                ALTER TABLE deletion_status
                ALTER COLUMN id SET DEFAULT nextval('{seq_name}')
            """))
            session.commit()

            # Step 6: 同步序列当前值，避免主键冲突
            result = session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM deletion_status"))
            next_val = result.scalar()
            session.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH {next_val}"))
            session.commit()

    except Exception as e:
        logger.warning(f"Could not ensure deletion_status table: {e}")


def get_db_version() -> str:
    """读取数据库当前已应用的 schema 版本号。"""
    _ensure_version_tracking_table()
    try:
        with get_sync_session() as session:
            result = session.execute(
                text("SELECT version FROM deletion_status ORDER BY id DESC LIMIT 1")
            )
            version = result.scalar_one_or_none()
            return version if version else "0.0.0"
    except Exception as e:
        logger.warning(f"Could not read database schema version: {e}")
        return "0.0.0"


def mark_schema_version(version: str):
    """在 deletion_status 表中记录一个 schema 版本已被应用。"""
    try:
        with get_sync_session() as session:
            session.execute(
                text("INSERT INTO deletion_status (version, description) VALUES (:ver, :desc)"),
                {"ver": version, "desc": f"Schema migration applied: version {version}"},
            )
            session.commit()
            logger.info(f"Schema version {version} recorded in database")
    except Exception as e:
        logger.warning(f"Could not record schema version {version}: {e}")


# ============================================================
#  Versioned Schema Migrations
# ============================================================

def _migration_v1_0_3(tables: list):
    """
    v1.0.3 迁移：Argo 之前累积的字段新增。
    包含 first_op、mineru_api_url、mineru_backend、skip_meta 四个列。
    使用 IF NOT EXISTS 检查，幂等可重复执行。
    """
    logger.info("--- Applying schema migration v1.0.3 (pre-Argo column additions) ---")
    steps = [
        ("add_first_op_column", add_first_op_column),
        ("add_mineru_api_url_column", add_mineru_api_url_column),
        ("add_mineru_backend_column", add_mineru_backend_column),
        ("add_skip_meta_column", add_skip_meta_column),
    ]
    for name, fn in steps:
        try:
            fn()
        except Exception as e:
            logger.error(f"Migration v1.0.3 - {name} failed: {e}")


def _migration_v1_0_4(tables: list):
    """
    v1.0.4 迁移：Argo 升级 ——
      1. 删除 Celery 废弃字段（job_celery_uuid, job_celery_work_name, task_celery_uid）
      2. 新增 CSGHub 集成字段（owner_org_id, flow_id, cluster_id 等 56 个列）
      3. 兜底检测：自动补齐 ORM 中有而 DB 中无的字段 / 删除 DB 中有而 ORM 中无的字段
    """
    logger.info("--- Applying schema migration v1.0.4 (Argo upgrade) ---")
    steps = [
        ("drop_obsolete_columns", drop_obsolete_columns),
        ("add_csghub_integration_columns", add_csghub_integration_columns),
    ]
    for name, fn in steps:
        try:
            fn()
        except Exception as e:
            logger.error(f"Migration v1.0.4 - {name} failed: {e}")

    # 兜底安全检测：对比 ORM 模型与数据库实际结构的差异
    for name, fn in [
        ("sync_missing_columns_for_tables", lambda: sync_missing_columns_for_tables(tables)),
        ("auto_drop_obsolete_columns", lambda: auto_drop_obsolete_columns(tables)),
    ]:
        try:
            fn()
        except Exception as e:
            logger.error(f"Migration v1.0.4 safety check - {name} failed: {e}")


# 版本号 → 迁移函数 注册表
# 新增版本时只需在此追加条目即可
SCHEMA_MIGRATIONS = {
    "1.0.3": _migration_v1_0_3,
    "1.0.4": _migration_v1_0_4,
}


def run_schema_migrations(tables: list):
    """
    根据数据库当前版本与目标 SCHEMA_VERSION 的差异，按版本顺序执行所有未应用的迁移。

    版本记录存储在 deletion_status 表中，每条迁移成功后会插入一条记录。
    每个版本的迁移函数内部都是幂等的，即使重复执行也不会出错。
    """
    current_version = get_db_version()
    logger.info(f"Database schema version: current={current_version}, target={SCHEMA_VERSION}")

    current_tup = _version_to_tuple(current_version)

    # 找出所有 > current_version 的迁移版本，按版本号排序
    pending = sorted(
        [v for v in SCHEMA_MIGRATIONS if _version_to_tuple(v) > current_tup],
        key=_version_to_tuple,
    )

    if not pending:
        logger.info("Database schema is up to date, no migrations to apply")
        return

    logger.info(f"Pending schema migrations: {pending}")

    for version in pending:
        logger.info(f"--- Applying schema migration {version} ---")
        try:
            SCHEMA_MIGRATIONS[version](tables)
            mark_schema_version(version)
            logger.info(f"--- Schema migration {version} completed ---")
        except Exception as e:
            logger.error(f"Schema migration {version} failed: {e}")
            # 记录版本避免下次重复执行失败的迁移，同时不阻断启动
            try:
                mark_schema_version(version)
            except Exception:
                pass



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

    logger.info("Starting database versioned schema migrations...")
    run_schema_migrations(business_tables)
    logger.info("Database schema migrations completed")
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
