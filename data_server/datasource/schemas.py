from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime



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


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(DataSourceBase):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    extra_config: Optional[Dict] = None



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
    task_celery_uid: Optional[str] = None
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
