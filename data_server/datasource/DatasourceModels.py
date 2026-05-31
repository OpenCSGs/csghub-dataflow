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
    name = Column(String(100), nullable=False, comment="Data source name")
    des = Column(String(2048), comment="Data source description")
    source_type = Column(Integer, nullable=False, comment="DataSourceTypeEnum: data source type")
    host = Column(String(100), nullable=False, comment="Server address")
    port = Column(Integer, comment="Port number")
    auth_type = Column(String(20), comment="Authentication method")
    username = Column(String(100), comment="Username")
    password = Column(String(200), comment="Password")
    database = Column(String(100), comment="Database name")
    extra_config = Column(JSON, comment="Extra config; storage format depends on database type")
    source_status = Column(Integer,comment="DataSourceStatusEnum")
    owner_id = Column(Integer, comment="Owner user")
    owner_org_id = Column(String(255), comment="Owner organization ID")
    owner_org_name = Column(String(255), comment="Owner organization name")
    cluster_id = Column(String(255), comment="Default cluster ID")
    cluster_name = Column(String(255), comment="Default cluster name")
    resource_id = Column(Integer, comment="Default resource ID")
    resource_name = Column(String(255), comment="Default resource name")
    storage_size = Column(String(32), comment="Work volume storage size, e.g. 4Gi")
    namespace_uuid = Column(String(255), comment="namespace UUID in CSGHub DataFlow path")
    namespace_type = Column(String(32), comment="namespace scope: personal / organization")
    task_run_time = Column(DateTime, comment='Task start time')
    created_at = Column(DateTime, default=datetime.datetime.now, comment='Task creation time')
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='Last updated time')

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
            "owner_org_id": self.owner_org_id,
            "owner_org_name": self.owner_org_name,
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "storage_size": getattr(self, "storage_size", None),
            "namespace_uuid": getattr(self, "namespace_uuid", None),
            "namespace_type": getattr(self, "namespace_type", None),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            "task_run_time": self.task_run_time.strftime("%Y-%m-%d %H:%M:%S") if self.task_run_time else None,
            "datasource_type": DataSourceTypeEnum(self.source_type).name,
            "auth_type": self.auth_type,
        }



class CollectionTask(Base):
    __tablename__ = 'collection_tasks'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_uid = Column(String(100), comment="Unique task identifier")
    task_run_host = Column(String(30), comment="Server executing the task")
    datasource_id = Column(Integer, ForeignKey('datasources.id'), nullable=False)
    task_status = Column(Integer, nullable=False, comment="Task status")
    created_at = Column(DateTime, default=datetime.datetime.now, comment='Task creation time')
    total_count = Column(Integer, comment='Total record count')
    records_count = Column(Integer, comment='Processed record count')
    records_per_second = Column(Integer, comment='Records processed per second')
    start_run_at = Column(DateTime, comment='Run start time')
    csg_hub_server_branch = Column(String(100), comment="csghub-server branch name")
    end_run_at = Column(DateTime, comment='Run end time')
    flow_id = Column(String(32), comment="DataFlow global task ID submitted to CSGHub")
    cluster_id = Column(String(255), comment="Cluster ID selected when submitting to CSGHub")
    cluster_name = Column(String(255), comment="Cluster name selected when submitting to CSGHub")
    resource_id = Column(Integer, comment="Resource ID selected when submitting to CSGHub")
    resource_name = Column(String(255), comment="Resource name selected when submitting to CSGHub")
    storage_size = Column(String(32), comment="Work volume storage size, e.g. 4Gi")
    owner_id = Column(Integer, comment="User ID who triggered the task")
    owner_org_id = Column(String(255), comment="Organization ID who triggered the task")
    owner_org_name = Column(String(255), comment="Organization name who triggered the task")
    csghub_job_id = Column(String(100), comment="Job ID returned by CSGHub")
    csghub_status = Column(String(100), comment="Task status on CSGHub side")
    csghub_request_payload = Column(Text, comment="Request body for CSGHub task creation")
    csghub_response_payload = Column(Text, comment="Raw response from CSGHub")
    namespace_uuid = Column(String(255), comment="namespace UUID in CSGHub DataFlow path")
    namespace_type = Column(String(32), comment="namespace scope: personal / organization")
    is_active = Column(Boolean, default=True, comment="False means logically deleted")
    deleted_at = Column(DateTime, comment="Logical deletion time")
    datasource = relationship("DataSource", backref="tasks")

    def to_dict(self):
        from data_server.utils.workflow_sync_store import collection_task_export_aliases

        export_aliases = collection_task_export_aliases(self)
        return {
            "id": self.id,
            "task_uid": self.task_uid,
            "task_run_host": self.task_run_host,
            "datasource_id": self.datasource_id,
            "task_status": self.task_status,
            "flow_id": self.flow_id,
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "storage_size": getattr(self, "storage_size", None),
            "owner_id": self.owner_id,
            "owner_org_id": self.owner_org_id,
            "owner_org_name": self.owner_org_name,
            "namespace_uuid": getattr(self, "namespace_uuid", None),
            "namespace_type": getattr(self, "namespace_type", None),
            "csghub_job_id": self.csghub_job_id,
            "csghub_status": self.csghub_status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "total_count": self.total_count,
            "records_count": self.records_count,
            "records_per_second": self.records_per_second,
            "start_run_at": self.start_run_at.strftime("%Y-%m-%d %H:%M:%S") if self.start_run_at else None,
            "csg_hub_server_branch": self.csg_hub_server_branch,
            "end_run_at": self.end_run_at.strftime("%Y-%m-%d %H:%M:%S") if self.end_run_at else None,
            "export_repo_id": export_aliases.get("export_repo_id"),
            "export_branch_name": export_aliases.get("export_branch_name"),
            "datasource": self.datasource.to_json()
        }
