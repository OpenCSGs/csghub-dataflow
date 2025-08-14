from .base_ingester import Ingester
from typing import Union
from pathlib import Path
from data_engine.utils.env import GetHubEndpoint
import os
from pycsghub.utils import (build_csg_headers,
                            model_id_to_group_owner_name,
                            get_endpoint,
                            REPO_TYPE_DATASET)
from pycsghub.snapshot_download import snapshot_download
from loguru import logger
import uuid

class IngesterCSGHUB(Ingester):
    def __init__(
        self,
        dataset_path:str, 
        repo_id: str, 
        branch: str,
        user_name: str,
        user_token: str,
    ):
        self.dataset_path = dataset_path
        self.repo_id = repo_id
        self.branch = branch
        self.user_name = user_name
        self.user_token = user_token
        if self.repo_id is not None and len(self.repo_id) > 0:
            self.namespace, self.reponame = model_id_to_group_owner_name(self.repo_id)
        logger.info(f'Using dataset_path: {self.dataset_path}, repo:{self.repo_id}, branch:{self.branch}')
        self._src_path = self.dataset_path
        if not os.path.exists(self._src_path):
            os.makedirs(self._src_path, exist_ok=True)
            
    def ingest(self) -> Union[Path, None]:
        """
        Ingest data from different source to DEFAULT_SRC_PATH
        """
        # logger.info(f'downloading repo:{self.repo_id} with branch:{self.branch} to {self._src_path}')
        if self.repo_id is not None and len(self.repo_id) > 0:
            logger.info(f'model_id:{self.repo_id}')
            endpoint = get_endpoint(endpoint=GetHubEndpoint())
            logger.info(f'endpoint:{endpoint}')
            logger.info(f'入参:repo_id:{self.repo_id}, repo_type:{REPO_TYPE_DATASET}, revision:{self.branch}, cache_dir:{self._src_path}, endpoint:{endpoint}, token:{self.user_token}')
            result = snapshot_download(
                repo_id=self.repo_id,
                repo_type=REPO_TYPE_DATASET,
                revision=self.branch,
                cache_dir=self._src_path,
                endpoint=endpoint,
                token=self.user_token
            )
            logger.info(f'result:{result}')
            return result
        else:
            logger.info(f'Using local path: {self._src_path}')
            return self._src_path

