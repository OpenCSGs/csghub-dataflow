from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
import datetime
from enum import Enum

Base = declarative_base()



class DataFormatTypeEnum(Enum):
    PPT = 0  # ppt
    Word = 1  # word
    Markdown = 2  # markdown
    Excel = 3  # excel
    Json = 4  # json
    Csv = 5  # csv
    Parquet = 6  # parquet
    PDF = 7  # pdf
    Txt = 8  # plain text
    Html = 9  # html


def getFormatTypeName(type):
    for item in DataFormatTypeEnum:
        if item.value == type:
            return item.name



class DataFormatTaskStatusEnum(Enum):
    WAITING = 0
    EXECUTING = 1
    COMPLETED = 2
    ERROR = 3
    STOP = 4



class DataFormatTask(Base):
    __tablename__ = 'data_format_tasks'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="Task name")
    des = Column(String(2048), comment="Task description")
    from_csg_hub_dataset_name = Column(String(100), comment="CSG Hub source dataset name")
    from_csg_hub_dataset_id = Column(Integer, comment="CSG Hub source dataset ID")
    from_csg_hub_repo_id = Column(String(100), comment="CSG Hub source repo ID")
    from_csg_hub_dataset_branch = Column(String(100), comment="CSG Hub source dataset branch")
    from_data_type = Column(Integer, comment="Source format type DataFormatTypeEnum")
    to_csg_hub_dataset_name = Column(String(100), comment="CSG Hub target dataset name")
    to_csg_hub_dataset_id = Column(Integer, comment="CSG Hub target dataset ID")
    to_csg_hub_repo_id = Column(String(100), comment="CSG Hub target repo ID")
    to_csg_hub_dataset_default_branch = Column(String(100), comment="CSG Hub target dataset default branch main/master")
    to_data_type = Column(Integer, comment="Target format type DataFormatTypeEnum")
    task_uid = Column(String(100), comment="Unique task identifier")
    task_status = Column(Integer, nullable=False, comment="Task status DataFormatTaskStatusEnum enum")
    owner_id = Column(Integer, comment="Owner user")
    owner_org_id = Column(String(255), comment="Owner organization ID")
    owner_org_name = Column(String(255), comment="Owner organization name")
    mineru_api_url = Column(String(500), comment="MinerU API URL")
    mineru_backend = Column(String(100), comment="MinerU backend type")
    skip_meta = Column(Boolean, default=False, comment="If True, generate and upload meta.log; if False, skip meta.log")
    flow_id = Column(String(32), comment="DataFlow global task ID submitted to CSGHub")
    cluster_id = Column(String(255), comment="Cluster ID selected when submitting to CSGHub")
    cluster_name = Column(String(255), comment="Cluster name selected when submitting to CSGHub")
    resource_id = Column(Integer, comment="Resource ID selected when submitting to CSGHub")
    resource_name = Column(String(255), comment="Resource name selected when submitting to CSGHub")
    storage_size = Column(String(32), comment="Work volume storage size, e.g. 4Gi")
    csghub_job_id = Column(String(100), comment="Job ID returned by CSGHub")
    csghub_status = Column(String(100), comment="Task status on CSGHub side")
    csghub_request_payload = Column(Text, comment="Request body for CSGHub task creation")
    csghub_response_payload = Column(Text, comment="Raw response from CSGHub")
    namespace_uuid = Column(String(255), comment="namespace UUID in CSGHub DataFlow path")
    namespace_type = Column(String(32), comment="namespace scope: personal / organization")
    start_run_at = Column(DateTime, comment='Run start time')
    end_run_at = Column(DateTime, comment='Run end time')
    created_at = Column(DateTime, default=datetime.datetime.now, comment='Task creation time')
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='Last updated time')
    is_active = Column(Boolean, default=True, comment="False means logically deleted")
    deleted_at = Column(DateTime, comment="Logical deletion time")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "des": self.des,
            "from_csg_hub_dataset_name": self.from_csg_hub_dataset_name,
            "from_csg_hub_dataset_id": self.from_csg_hub_dataset_id,
            "from_csg_hub_repo_id": self.from_csg_hub_repo_id,
            "from_csg_hub_dataset_branch": self.from_csg_hub_dataset_branch,
            "from_data_type": self.from_data_type,
            "to_csg_hub_dataset_name": self.to_csg_hub_dataset_name,
            "to_csg_hub_dataset_id": self.to_csg_hub_dataset_id,
            "to_csg_hub_repo_id": self.to_csg_hub_repo_id,
            "to_csg_hub_dataset_default_branch": self.to_csg_hub_dataset_default_branch,
            "to_data_type": self.to_data_type,
            "task_uid": self.task_uid,
            "task_status": self.task_status,
            "owner_id": self.owner_id,
            "owner_org_id": self.owner_org_id,
            "owner_org_name": self.owner_org_name,
            "namespace_uuid": getattr(self, "namespace_uuid", None),
            "namespace_type": getattr(self, "namespace_type", None),
            "mineru_api_url": self.mineru_api_url,
            "mineru_backend": self.mineru_backend,
            "skip_meta": getattr(self, 'skip_meta', False),  # Use getattr to handle missing column
            "flow_id": self.flow_id,
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "storage_size": getattr(self, "storage_size", None),
            "csghub_job_id": self.csghub_job_id,
            "csghub_status": self.csghub_status,
            "start_run_at": self.start_run_at,
            "end_run_at": self.end_run_at,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
