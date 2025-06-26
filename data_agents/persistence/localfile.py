from .base import Persistence
from typing import Mapping, Any
import os
import json
import pathlib
from dataclasses import dataclass
from autogen_core.models import (
    UserMessage,
)
import glob

PERSISTANCE_DIR = 'configs/persistances'

@dataclass
class Record:
    content: str
    source: str

class LocalFilePersistence(Persistence):
    def load_content(self, uuid) -> Mapping[str, Any]:
        base_dir = pathlib.Path().resolve()
        persistance_path = os.path.join(base_dir, PERSISTANCE_DIR, uuid + '.json')
        try:
            with open(persistance_path) as file:
                content = json.load(file)
        except FileNotFoundError:
            return None
        
        def to_obj(value):
            value["memory"]["messages"] = [UserMessage(content=item["content"], source=item["source"]) for item in value["memory"]["messages"]]
            return value

        content = {key: to_obj(value) for key, value in content.items()}
        return content

    def save_content(self, uuid, content: Mapping[str, Any]) -> None:
        base_dir = pathlib.Path().resolve()
        persistance_path = os.path.join(base_dir, PERSISTANCE_DIR, uuid + '.json')

        def to_dict(value):
            value["memory"]["messages"] = [{"content": item.content, "source": item.source} for item in value["memory"]["messages"]]
            return value

        content = {key: to_dict(value) for key, value in content.items() if value != {}}
        if content:
            with open(persistance_path, "w") as file:
                file.write(json.dumps(content))

    def get_uuid(self, userid) -> str:
        base_dir = pathlib.Path().resolve()
        persistance_path = os.path.join(base_dir, PERSISTANCE_DIR, '*.json')
        json_files = glob.glob(persistance_path)
        for file in json_files:
            file_name = os.path.basename(file)
            if userid in file_name:
                return os.path.splitext(file_name)[0]
            
        return None

        