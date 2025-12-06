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
    name = Column(String(100), nullable=False, comment="任务名称")
    des = Column(String(2048), comment="任务描述")
    from_csg_hub_dataset_name = Column(String(100), comment="CSG Hub 源数据集名称")
    from_csg_hub_dataset_id = Column(Integer, comment="CSG Hub 源数据集ID")
    from_csg_hub_repo_id = Column(String(100), comment="CSG Hub 源仓库ID")
    from_csg_hub_dataset_branch = Column(String(100), comment="CSG Hub 源数据集分支")
    from_data_type = Column(Integer, comment="转换源类型 DataFormatTypeEnum")
    to_csg_hub_dataset_name = Column(String(100), comment="CSG Hub 存储数据集名称")
    to_csg_hub_dataset_id = Column(Integer, comment="CSG Hub 存储数据集ID")
    to_csg_hub_repo_id = Column(String(100), comment="CSG Hub 存储仓库ID")
    to_csg_hub_dataset_default_branch = Column(String(100), comment="CSG Hub 存储数据集默认分支 main/master")
    to_data_type = Column(Integer, comment="转换目标类型DataFormatTypeEnum ")
    task_uid = Column(String(100), comment="任务唯一标识")
    task_celery_uid = Column(String(100), comment="celery任务调度唯一标识")
    task_status = Column(Integer, nullable=False, comment="任务状态 DataFormatTaskStatusEnum 枚举")
    owner_id = Column(Integer, comment="所属用户")
    mineru_api_url = Column(String(500), comment="MinerU API 地址")
    mineru_backend = Column(String(100), comment="MinerU 后端类型")
    skip_meta = Column(Boolean, default=False, comment="如果为 True，则生成并上传 meta.log 文件；如果为 False，则不生成 meta.log 文件")
    start_run_at = Column(DateTime, comment='运行开始时间')
    end_run_at = Column(DateTime, comment='运行结束时间')
    created_at = Column(DateTime, default=datetime.datetime.now, comment='任务创建时间')
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='更新时间')

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
            "task_celery_uid": self.task_celery_uid,
            "task_status": self.task_status,
            "owner_id": self.owner_id,
            "mineru_api_url": self.mineru_api_url,
            "mineru_backend": self.mineru_backend,
            "skip_meta": getattr(self, 'skip_meta', False),  # Use getattr to handle missing column
            "start_run_at": self.start_run_at,
            "end_run_at": self.end_run_at,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
