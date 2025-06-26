from typing import Mapping, Any
from abc import ABC, abstractmethod


class Persistence(ABC):
    def __init__(self):
        pass
    
    @abstractmethod
    def load_content(self, userid) -> Mapping[str, Any]:
        pass

    @abstractmethod
    def save_content(self, userid, content: Mapping[str, Any]) -> None:
        pass

    @abstractmethod
    def get_uuid(self, userid) -> str:
        pass