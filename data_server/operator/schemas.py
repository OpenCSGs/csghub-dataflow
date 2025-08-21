from typing import Any, Union, Dict
from pydantic import BaseModel, field_serializer
from datetime import datetime
from typing import Optional, List

class OperatorInfoResponse(BaseModel):
    id: Optional[int] = None
    operator_name: Optional[str] = None
    operator_type: Optional[str] = None
    execution_order: Optional[int] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None
    before_cleaning: Optional[str] = None
    after_cleaning: Optional[str] = None
    icon: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_public: Optional[bool] = None

    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    class Config:
        from_attributes = True

class OperatorConfigResponse(BaseModel):
    id: Optional[int] = None
    operator_id: Optional[int] = None
    config_name: Optional[str] = None
    config_type: Optional[str] = None
    select_options: Optional[Union[List[int], List[Dict[str, Any]]]] = None
    default_value: Optional[Union[str, Dict[str, Any]]] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    slider_step: Optional[str] = None
    is_required: Optional[bool] = None
    is_spinner: Optional[bool] = None
    spinner_step: Optional[str] = None
    final_value: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    class Config:
        from_attributes = True

class OperatorResponse(OperatorInfoResponse):
    configs: List[OperatorConfigResponse] = []

    class Config:
        from_attributes = True

class OperatorPermissionResponse(BaseModel):
    id: Optional[int] = None
    operator_id: Optional[int] = None
    uuid: Optional[str] = None
    username: Optional[str] = None
    role_type: Optional[int] = None
    name: Optional[str] = None
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    class Config:
        from_attributes = True

class OperatorConfigRequest(BaseModel):
    id: Optional[int] = None
    config_name: str
    config_type: str
    select_options: Optional[List[int]] = None
    default_value: Optional[str] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    slider_step: Optional[str] = None
    is_required: Optional[bool] = True
    is_spinner: Optional[bool] = False
    spinner_step: Optional[str] = None
    final_value: Optional[Any] = None

class OperatorCreateRequest(BaseModel):
    operator_name: str
    operator_type: str
    execution_order: Optional[int] = 0
    is_enabled: Optional[bool] = True
    description: Optional[str] = None
    before_cleaning: Optional[str] = None
    after_cleaning: Optional[str] = None
    icon: Optional[str] = None
    configs: Optional[List[OperatorConfigRequest]] = []

class OperatorUpdateRequest(BaseModel):
    operator_name: Optional[str] = None
    operator_type: Optional[str] = None
    execution_order: Optional[int] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None
    before_cleaning: Optional[str] = None
    after_cleaning: Optional[str] = None
    icon: Optional[str] = None
    is_public: Optional[bool] = None
    configs: Optional[List[OperatorConfigRequest]] = None

class OperatorConfigSelectOptionsCreate(BaseModel):
    name: str
    is_enable: bool = True
    sort: int = 0

class OperatorConfigSelectOptionsResponse(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    is_enable: Optional[bool] = None
    sort: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    class Config:
        from_attributes = True

class UserPermission(BaseModel):
    uuid: str
    username: Optional[str] = None

class OrgPermission(BaseModel):
    name: str
    path: str

class OperatorPermissionCreateRequest(BaseModel):
    operator_id: int
    users: Optional[List[UserPermission]] = []
    orgs: Optional[List[OrgPermission]] = []
