
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
import os
import uuid
from data_engine.utils.env import DEFAULT_SRC_PATH

class Ingester(ABC):

    def __init__(
        self,
        dataset_path:str, 
        repo_path: str, 
        branch: str
    ):
        self.dataset_path = dataset_path
        self.repo_path = repo_path
        self.branch = branch
        self._src_path = os.path.join(DEFAULT_SRC_PATH, str(uuid.uuid4()))
        
    @abstractmethod
    def ingest(self) -> Union[Path, None]:
        """
        Ingest data from different source to DEFAULT_SRC_PATH
        """

    @property
    def src_path(self):
        return self._src_path