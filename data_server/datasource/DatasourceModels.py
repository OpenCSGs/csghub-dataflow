from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
import datetime
import json
from enum import Enum
from data_server.database.bean.base import Base



class DataSourceTypeEnum(Enum):
    MYSQL = 1  # MYSQL
    MONGODB = 2  # MONGODB
    FILE = 3  # FILE
    HIVE = 4  # HIVE


class DataSourceStatusEnum(Enum):
    INACTIVE = 0  # Connection failed
    ACTIVE = 1  # Connection is normal
    WAITING = 2  # To be executed


class DataSourceTaskStatusEnum(Enum):
    WAITING = 0
    EXECUTING = 1
    COMPLETED = 2
    ERROR = 3
    STOP = 4


class DataSource(Base):
    __tablename__ = 'datasources'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="数据源名称")
    des = Column(String(2048), comment="数据源描述")
    source_type = Column(Integer, nullable=False, comment="DataSourceTypeEnum 枚举 数据源类型")
    host = Column(String(100), nullable=False, comment="服务器地址")
    port = Column(Integer, comment="端口号")
    auth_type = Column(String(20), comment="认证方式")
    username = Column(String(100), comment="用户名")
    password = Column(String(200), comment="密码")
    database = Column(String(100), comment="数据库名")
    extra_config = Column(JSON, comment="额外配置,具体存储根据数据库类型而定")
    source_status = Column(Integer,comment="DataSourceStatusEnum 枚举")
    owner_id = Column(Integer, comment="所属用户")
    task_run_time = Column(DateTime, comment='任务开始时间')
    created_at = Column(DateTime, default=datetime.datetime.now, comment='任务创建时间')
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='更新时间')

    def to_json(self):
        # Handle extra_config, ensure correct parsing and return
        extra_config_raw = self.extra_config
        extra_config_dict = None
        
        # Parse extra_config
        if isinstance(extra_config_raw, str):
            try:
                extra_config_dict = json.loads(extra_config_raw)
            except (json.JSONDecodeError, TypeError):
                extra_config_dict = None
        elif isinstance(extra_config_raw, dict):
            extra_config_dict = extra_config_raw.copy()
        
        # Handle branch field: keep csg_hub_dataset_default_branch as is (read from database, no modification), also add csg_hub_dataset_branch
        if extra_config_dict is not None:
            # Get value of csg_hub_dataset_default_branch (if exists) to set csg_hub_dataset_branch
            # Keep csg_hub_dataset_default_branch as is, no modification
            branch_value = extra_config_dict.get("csg_hub_dataset_default_branch")
            if not branch_value or (isinstance(branch_value, str) and branch_value.strip() == ""):
                branch_value = "main"
            
            # Add csg_hub_dataset_branch field (get value from csg_hub_dataset_default_branch, use main if not exists)
            extra_config_dict["csg_hub_dataset_branch"] = branch_value
            
            # csg_hub_dataset_default_branch remains unchanged (return if exists in database, don't add if not)
            
            # Convert updated dictionary back to JSON string format
            extra_config = json.dumps(extra_config_dict, ensure_ascii=False, indent=4)
        else:
            # If extra_config is empty, return empty config as is
            extra_config = extra_config_raw if extra_config_raw else "{}"
        
        return {
            "id": self.id,
            "name": self.name,
            "des": self.des,
            "source_type": self.source_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "database": self.database,
            "extra_config": extra_config,
            "source_status": self.source_status,
            "owner_id": self.owner_id,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            "task_run_time": self.task_run_time.strftime("%Y-%m-%d %H:%M:%S") if self.task_run_time else None,
            "datasource_type": DataSourceTypeEnum(self.source_type).name,
            "auth_type": self.auth_type,
        }



class CollectionTask(Base):
    __tablename__ = 'collection_tasks'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_uid = Column(String(100), comment="任务唯一标识")
    task_run_host = Column(String(30), comment="任务执行的服务器")
    task_celery_uid = Column(String(100), comment="celery任务调度唯一标识")
    datasource_id = Column(Integer, ForeignKey('datasources.id'), nullable=False)
    task_status = Column(Integer, nullable=False, comment="任务状态")
    created_at = Column(DateTime, default=datetime.datetime.now, comment='任务创建时间')
    total_count = Column(Integer, comment='总条数')
    records_count = Column(Integer, comment='已处理条数')
    records_per_second = Column(Integer, comment='每秒处理条数')
    start_run_at = Column(DateTime, comment='运行开始时间')
    csg_hub_server_branch = Column(String(100), comment="csghub-server 分支名称")
    end_run_at = Column(DateTime, comment='运行结束时间')
    datasource = relationship("DataSource", backref="tasks")

    def to_dict(self):
        return {
            "id": self.id,
            "task_uid": self.task_uid,
            "task_run_host": self.task_run_host,
            "task_celery_uid": self.task_celery_uid,
            "datasource_id": self.datasource_id,
            "task_status": self.task_status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "total_count": self.total_count,
            "records_count": self.records_count,
            "records_per_second": self.records_per_second,
            "start_run_at": self.start_run_at.strftime("%Y-%m-%d %H:%M:%S") if self.start_run_at else None,
            "csg_hub_server_branch": self.csg_hub_server_branch,
            "end_run_at": self.end_run_at.strftime("%Y-%m-%d %H:%M:%S") if self.end_run_at else None,
            "datasource": self.datasource.to_json()
        }
