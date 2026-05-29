import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, Request
from loguru import logger
from data_server.utils.project_paths import get_project_root

class FileStorageManager:

    
    def __init__(self, base_url: str = "http://localhost:8000"):


        self.base_url = base_url.rstrip('/')

        self.project_root = get_project_root()
        self.upload_dir = Path(os.path.join(self.project_root, 'attach'))
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
    def save_uploaded_file(self, file: UploadFile, category: str = "comment", request: Optional[Request] = None) -> Tuple[str, str]:

        try:

            file_id = str(uuid.uuid4())
            

            file_extension = ""
            if file.filename:
                file_extension = Path(file.filename).suffix
            

            category_dir = self.upload_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            file_name = f"{file_id}{file_extension}"
            file_path = category_dir / file_name
            

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            

            file_code = f"{category}/{file_id}"
            

            file_url = f"api/v1/dataflow/real_static_files/{category}/{file_name}"
            
            logger.info(f"File saved successfully: {file_path}, code: {file_code}")
            
            return file_code, file_url
            
        except Exception as e:
            logger.error(f"Failed to save file: {str(e)}")
            raise

    def delete_file_by_name(self, filename: str, category: str = "operator") -> bool:

        try:

            category_dir = self.upload_dir / category
            if not category_dir.exists():
                logger.warning(f"Category directory does not exist: {category_dir}")
                return False

            file_path = category_dir / filename


            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return False


            file_path.unlink()
            logger.info(f"File deleted successfully: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False


file_storage_manager = FileStorageManager()
