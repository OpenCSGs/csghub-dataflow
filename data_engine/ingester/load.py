from .base_ingester import Ingester
from .csghub_ingester import IngesterCSGHUB

def load_ingester(
    dataset_path:str, 
    repo_id: str, 
    branch: str,
    user_name: str,
    user_token: str,
) -> Ingester:
    return IngesterCSGHUB(
        dataset_path=dataset_path, 
        repo_id=repo_id,
        branch=branch,
        user_name=user_name,
        user_token=user_token
    )