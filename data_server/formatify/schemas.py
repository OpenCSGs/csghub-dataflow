from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any


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
