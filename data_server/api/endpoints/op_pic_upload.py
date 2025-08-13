from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request
from typing import Dict, Any
import os
from loguru import logger
from data_server.utils.file_storage import file_storage_manager
from data_server.schemas.responses import response_success, response_fail


op_pic_router = APIRouter()


@op_pic_router.post("/internal_api/upload", summary="上传operator图片")
async def upload_image(
    request: Request,
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    上传图片文件接口

    ## 功能说明
    - 支持上传图片文件（jpg, jpeg, png, gif, bmp, webp等格式）
    - 自动生成唯一的文件标识码
    - 返回文件访问URL

    ## 参数说明
    - **file**: 要上传的图片文件

    ## 返回值格式
    ```json
    {
        "code": "operator/f41dd59d-b462-412b-88e9-9c4da481a9d4",
        "url": "/files/operator/f41dd59d-b462-412b-88e9-9c4da481a9d4.jpg"
    }
    ```

    ## 错误情况
    - 文件为空：返回400错误
    - 文件格式不支持：返回400错误
    - 文件保存失败：返回500错误
    """
    try:
        # 检查文件是否为空
        if not file or not file.filename:
            return response_fail(msg="请选择要上传的文件")
        
        # 检查文件大小（从环境变量读取限制）
        max_file_size = int(os.getenv("UPLOAD_MAX_FILE_SIZE", "104857600"))  # 默认100MB
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size == 0:
            return response_fail(msg="文件内容为空")
        
        if file_size > max_file_size:
            max_size_mb = max_file_size // (1024 * 1024)
            return response_fail(msg=f"文件大小不能超过{max_size_mb}MB")
        
        # 支持文件类型（从环境变量读取）
        allowed_extensions_str = os.getenv("UPLOAD_ALLOWED_EXTENSIONS", ".jpg,.jpeg,.png,.gif,.bmp,.webp,.svg")
        allowed_extensions = set(ext.strip() for ext in allowed_extensions_str.split(','))
        # 获取文件扩展名
        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        if f'.{file_extension}' not in allowed_extensions:
            return response_fail(msg=f"不支持的文件格式，仅支持: {', '.join(allowed_extensions)}")
        
        # 重置文件指针
        file.file.seek(0)
        
        # 保存文件
        file_code, file_url = file_storage_manager.save_uploaded_file(file, category="operator", request=request)

        # 返回结果
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
    """
    根据文件名删除上传的文件

    ## 参数说明
    - **filename**: 文件名（包含扩展名），如 "abc123.jpg"

    ## 返回值
    - 删除成功：返回成功消息
    - 删除失败：返回错误信息

    ## 使用示例
    DELETE /api/v1/dataflow/internal_api/delete/abc123.jpg
    """
    try:
        # 使用新的删除方法
        success = file_storage_manager.delete_file_by_name(filename, category="operator")

        if success:
            logger.info(f"文件删除成功: {filename}")
            return response_success(msg="文件删除成功")
        else:
            return response_fail(msg="文件不存在或删除失败")

    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return response_fail(msg=f"删除文件失败: {str(e)}")
