from pydantic import BaseModel, field_validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from data_server.utils.storage_size import normalize_storage_size



class DataSourceBase(BaseModel):
    name: str
    des: str
    source_type: int
    host: str
    auth_type: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: str
    extra_config: Optional[Dict] = None
    source_status: Optional[int] = None
    # Whether to execute (default is not to execute)
    is_run: Optional[bool] = False
    task_run_time: Optional[datetime] = None
    cluster_id: Optional[str] = None
    cluster_name: Optional[str] = None
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    storage_size: Optional[str] = None
    namespace_uuid: Optional[str] = None
    namespace_type: Optional[str] = "personal"

    @field_validator("storage_size", mode="before")
    @classmethod
    def validate_storage_size(cls, value):
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return None
        return normalize_storage_size(value)


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    extra_config: Optional[Dict] = None
    namespace_uuid: Optional[str] = None
    namespace_type: Optional[str] = None


class DataSourceResponse(BaseModel):
    id: int
    name: str
    des: Optional[str] = None
    source_type: int
    host: str
    port: Optional[int] = None
    username: Optional[str] = None
    database: str
    extra_config: Optional[Dict] = None
    source_status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True



class CollectionTaskBase(BaseModel):
    name: str
    datasource_id: int
    query: str
    schedule: Optional[str] = None
    is_active: Optional[bool] = True


class CollectionTaskCreate(CollectionTaskBase):
    pass


class CollectionTaskUpdate(CollectionTaskBase):
    name: Optional[str] = None
    datasource_id: Optional[int] = None
    query: Optional[str] = None
    schedule: Optional[str] = None
    is_active: Optional[bool] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None



class TableListResponse(BaseModel):
    tables: List[str]


class QueryResponse(BaseModel):
    status: str
    records_count: int
    data: List[Dict[str, Any]]


class CollectionTaskResponse(BaseModel):
    id: int
    task_uid: Optional[str] = None
    task_run_host: Optional[str] = None
    datasource_id: int
    task_status: int
    created_at: datetime
    total_count: Optional[int] = None
    records_count: Optional[int] = None
    records_per_second: Optional[int] = None
    start_run_at: Optional[datetime] = None
    csg_hub_server_branch: Optional[str] = None
    end_run_at: Optional[datetime] = None
    datasource: Optional[Dict] = None

    class Config:
        from_attributes = True


class TaskExecutionResponse(BaseModel):
    id: int
    task_id: Optional[int] = None
    query_text: Optional[str] = None
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    records_count: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
