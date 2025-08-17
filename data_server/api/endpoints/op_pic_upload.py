from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request
from typing import Dict, Any
import os
import base64
from pathlib import Path
from loguru import logger
from data_server.utils.file_storage import file_storage_manager
from data_server.schemas.responses import response_success, response_fail
from data_celery.utils import get_project_root


op_pic_router = APIRouter()
image_getter_router = APIRouter()


@op_pic_router.post("/internal_api/upload", summary="上传operator图片")
async def upload_image(
    request: Request,
    file: UploadFile = File(...)
) -> Dict[str, Any]:

    try:

        if not file or not file.filename:
            return response_fail(msg="请选择要上传的文件")
        

        max_file_size = int(os.getenv("UPLOAD_MAX_FILE_SIZE", "104857600"))
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size == 0:
            return response_fail(msg="文件内容为空")
        
        if file_size > max_file_size:
            max_size_mb = max_file_size // (1024 * 1024)
            return response_fail(msg=f"文件大小不能超过{max_size_mb}MB")
        

        allowed_extensions_str = os.getenv("UPLOAD_ALLOWED_EXTENSIONS", ".jpg,.jpeg,.png,.gif,.bmp,.webp,.svg")
        allowed_extensions = set(ext.strip() for ext in allowed_extensions_str.split(','))

        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        if f'.{file_extension}' not in allowed_extensions:
            return response_fail(msg=f"不支持的文件格式，仅支持: {', '.join(allowed_extensions)}")
        

        file.file.seek(0)
        

        file_code, file_url = file_storage_manager.save_uploaded_file(file, category="operator", request=request)


        result = {
            "code": file_code,
            "url": file_url
        }

        logger.info(f"图片上传成功: {file.filename} -> {file_code}")
        return response_success(result)
        
    except Exception as e:
        logger.error(f"图片上传失败: {str(e)}")
        return response_fail(msg=f"图片上传失败: {str(e)}")


@op_pic_router.delete("/internal_api/delete/{filename}", summary="根据文件名删除上传的文件")
async def delete_uploaded_file_by_name(filename: str) -> Dict[str, Any]:

    try:

        success = file_storage_manager.delete_file_by_name(filename, category="operator")

        if success:
            logger.info(f"文件删除成功: {filename}")
            return response_success(msg="文件删除成功")
        else:
            return response_fail(msg="文件不存在或删除失败")

    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return response_fail(msg=f"删除文件失败: {str(e)}")


@image_getter_router.get("/real_static_files/{category}/{filename}", summary="obtain_the_base64_encoding_of_the_image")
async def get_image_base64(category: str, filename: str):
    try:
        project_root = get_project_root()
        image_path = Path(project_root) / 'attach' / category / filename
        
        if not image_path.exists() or not image_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        
        file_extension = filename.split('.')[-1].lower()
        mime_type = f"image/{file_extension}"
        if file_extension == 'svg':
            mime_type = "image/svg+xml"

        base64_image = encoded_string
        
        return response_success(data={base64_image})

    except HTTPException as http_exc:
        logger.warning(f"failed-to-obtain-the-picture: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"base64_encoding_failed: {str(e)}")
        return response_fail(msg=f"failed_to_obtain_the_picture: {str(e)}")
