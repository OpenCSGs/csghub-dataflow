from sqlalchemy.orm import Session
from typing import Optional
from fastapi import UploadFile
from datetime import datetime
from loguru import logger
from data_server.operator.models.operator import OperatorDocument, OperatorInfo
from data_server.operator.schemas import OperatorDocumentResponse


def get_document(db: Session, operator_id: int) -> Optional[OperatorDocumentResponse]:
    """查询算子的文档"""
    try:
        document = db.query(OperatorDocument).filter(
            OperatorDocument.operator_id == operator_id
        ).first()
        
        if not document:
            return None
        
        return OperatorDocumentResponse.model_validate(document)
    except Exception as e:
        logger.error(f"查询文档失败: {str(e)}")
        raise


async def upload_document(db: Session, operator_id: int, file: UploadFile) -> OperatorDocumentResponse:
    """上传文档：读取md文件内容并存储到数据库"""
    try:
        # 验证文件类型
        if not file.filename or not file.filename.endswith('.md'):
            raise ValueError("仅支持 .md 格式文件")
        
        # 检查算子是否存在
        operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
        if not operator:
            raise ValueError("算子不存在")
        
        # 读取文件内容
        content_bytes = await file.read()
        content_str = content_bytes.decode('utf-8')
        
        # 验证内容不为空
        if not content_str.strip():
            raise ValueError("文档内容不能为空")
        
        # 验证文件大小（10MB限制）
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content_bytes) > max_size:
            raise ValueError(f"文档大小不能超过 {max_size // (1024 * 1024)}MB")
        
        # 查找是否已有文档
        existing_doc = db.query(OperatorDocument).filter(
            OperatorDocument.operator_id == operator_id
        ).first()
        
        if existing_doc:
            # 更新现有文档
            existing_doc.content = content_str
            existing_doc.updated_at = datetime.now()
            db.commit()
            db.refresh(existing_doc)
            logger.info(f"更新算子 {operator_id} 的文档成功")
            return OperatorDocumentResponse.model_validate(existing_doc)
        else:
            # 创建新文档
            new_doc = OperatorDocument(
                operator_id=operator_id,
                content=content_str
            )
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)
            logger.info(f"创建算子 {operator_id} 的文档成功")
            return OperatorDocumentResponse.model_validate(new_doc)
            
    except UnicodeDecodeError:
        raise ValueError("文件编码错误，请使用 UTF-8 编码")
    except Exception as e:
        db.rollback()
        logger.error(f"上传文档失败: {str(e)}")
        raise


def delete_document(db: Session, operator_id: int) -> bool:
    """删除算子的文档"""
    try:
        document = db.query(OperatorDocument).filter(
            OperatorDocument.operator_id == operator_id
        ).first()
        
        if not document:
            return False
        
        db.delete(document)
        db.commit()
        logger.info(f"删除算子 {operator_id} 的文档成功")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"删除文档失败: {str(e)}")
        raise

