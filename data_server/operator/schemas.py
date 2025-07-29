from typing import Any, Union, Dict
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum
from typing import List

# 算子信息响应模型
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

    class Config:
        from_attributes = True

# 算子配置响应模型
class OperatorConfigResponse(BaseModel):
    id: Optional[int] = None
    operator_id: Optional[int] = None
    config_name: Optional[str] = None
    config_type: Optional[str] = None
    select_options: Optional[Union[List[int], List[Dict[str, Any]]]] = None  # 支持id列表或{value, label}格式
    default_value: Optional[Union[str, Dict[str, Any]]] = None  # 支持字符串或{value, label}格式
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    slider_step: Optional[str] = None
    is_required: Optional[bool] = None
    is_spinner: Optional[bool] = None
    spinner_step: Optional[str] = None
    final_value: Optional[Any] = None  # 用户最终选择的值
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# 组合响应模型，包含算子信息和配置列表
class OperatorResponse(OperatorInfoResponse):
    # 算子配置列表 - 继承自OperatorInfoResponse，并添加configs字段
    configs: List[OperatorConfigResponse] = []

    class Config:
        from_attributes = True

# 算子权限响应模型
class OperatorPermissionResponse(BaseModel):
    id: Optional[int] = None
    operator_id: Optional[int] = None
    uuid: Optional[str] = None
    username: Optional[str] = None
    role_type: Optional[int] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# 算子配置创建/更新请求模型
class OperatorConfigRequest(BaseModel):
    id: Optional[int] = None  # 更新时需要提供，创建时不需要
    config_name: str
    config_type: str
    select_options: Optional[List[int]] = None  # 多选id列表
    default_value: Optional[str] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    slider_step: Optional[str] = None
    is_required: Optional[bool] = True
    is_spinner: Optional[bool] = False
    spinner_step: Optional[str] = None
    final_value: Optional[Any] = None  # 用户最终选择的值

# 算子创建请求模型
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

# 算子更新请求模型
class OperatorUpdateRequest(BaseModel):
    operator_name: Optional[str] = None
    operator_type: Optional[str] = None
    execution_order: Optional[int] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None
    before_cleaning: Optional[str] = None
    after_cleaning: Optional[str] = None
    icon: Optional[str] = None
    configs: Optional[List[OperatorConfigRequest]] = None

# operator_config_select_options 创建请求模型
class OperatorConfigSelectOptionsCreate(BaseModel):
    name: str
    is_enable: bool = True
    sort: int = 0

# operator_config_select_options 响应模型
class OperatorConfigSelectOptionsResponse(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    is_enable: Optional[bool] = None
    sort: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True