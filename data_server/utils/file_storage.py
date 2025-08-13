import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, Request
from loguru import logger
from data_celery.utils import get_project_root

class FileStorageManager:
    """文件存储管理器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化文件存储管理器
        
        Args:
            base_url: 服务器基础URL，用于生成文件访问链接
        """
        # 移除尾部所有斜杠
        self.base_url = base_url.rstrip('/')
        # 设置上传路径
        self.project_root = get_project_root()
        self.upload_dir = Path(os.path.join(self.project_root, 'attach'))
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
    def save_uploaded_file(self, file: UploadFile, category: str = "comment", request: Optional[Request] = None) -> Tuple[str, str]:
        """
        保存上传的文件
        
        Args:
            file: 上传的文件对象
            category: 文件分类（如comment、operator等）
            request: FastAPI请求对象，用于动态获取基础URL

        Returns:
            Tuple[str, str]: (文件代码, 文件访问URL)
        """
        try:
            # 生成唯一的文件ID
            file_id = str(uuid.uuid4())
            
            # suffix: 获取文件扩展名(带'.')
            file_extension = ""
            if file.filename:
                file_extension = Path(file.filename).suffix
            
            # 构建文件路径
            category_dir = self.upload_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            file_name = f"{file_id}{file_extension}"
            file_path = category_dir / file_name
            
            # 保存文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 生成文件代码和相对URL（不包含IP和端口）
            file_code = f"{category}/{file_id}"
            
            # 返回相对路径，让前端动态拼接完整URL
            file_url = f"files/{category}/{file_name}"
            
            logger.info(f"文件保存成功: {file_path}, 代码: {file_code}")
            
            return file_code, file_url
            
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            raise

    def delete_file_by_name(self, filename: str, category: str = "operator") -> bool:
        """
        根据文件名删除文件

        Args:
            filename: 文件名（包含扩展名），如 "abc123.jpg"
            category: 文件分类，默认为 "operator"

        Returns:
            bool: 删除是否成功
        """
        try:
            # 构建文件路径
            category_dir = self.upload_dir / category
            if not category_dir.exists():
                logger.warning(f"分类目录不存在: {category_dir}")
                return False

            file_path = category_dir / filename

            # 检查文件是否存在
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return False

            # 删除文件
            file_path.unlink()
            logger.info(f"文件删除成功: {file_path}")
            return True

        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False

# 全局文件存储管理器实例
file_storage_manager = FileStorageManager()
