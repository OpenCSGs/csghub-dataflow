from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any
from data_server.utils.storage_size import normalize_storage_size


class DataFormatTaskRequest(BaseModel):
    name: Optional[str] = None
    des: Optional[str] = None
    from_csg_hub_dataset_name: Optional[str] = None
    from_csg_hub_dataset_id: Optional[int] = None
    from_csg_hub_dataset_branch: Optional[str] = None
    from_data_type: Optional[int] = None
    from_csg_hub_repo_id: Optional[str] = None
    to_csg_hub_dataset_name: Optional[str] = None
    to_csg_hub_dataset_id: Optional[int] = None
    to_csg_hub_dataset_default_branch: Optional[str] = None
    to_csg_hub_repo_id: Optional[str] = None
    to_data_type: Optional[int] = None
    mineru_api_url: Optional[str] = None
    mineru_backend: Optional[str] = None
    skip_meta: Optional[bool] = False  # If True, generate and upload meta.log; if False, skip meta.log
    cluster_id: Optional[str] = None
    cluster_name: Optional[str] = None
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    storage_size: Optional[str] = None
    namespace_uuid: Optional[str] = None
    namespace_type: str = "personal"

    @field_validator("storage_size", mode="before")
    @classmethod
    def validate_storage_size(cls, value):
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return None
        return normalize_storage_size(value)
