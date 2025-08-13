from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Annotated
from loguru import logger
from pydantic import BaseModel, Field

from data_server.api.dependencies import get_validated_token_payload
from data_server.database.session import get_sync_session
from data_server.algo_templates.mapper.algo_template_mapper import (
    get_template_by_id,
    create_template,
    update_template_by_id,
    delete_template_by_id,
    get_templates_by_query, find_repeat_name
)
from data_server.algo_templates.schemas import (
    AlgoTemplateCreate,
    AlgoTemplateUpdate,
    AlgoTemplateResponse,
    AlgoTemplateQuery
)
from data_server.schemas.responses import response_success, response_fail

router = APIRouter()


class AlgoTemplateListResponse(BaseModel):
    """算法模板列表响应模型"""
    templates: List[AlgoTemplateResponse] = Field(..., description="算法模板列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


@router.get("/", response_model=dict, summary="获取算法模板列表")
async def get_algo_templates(
    payload: Dict = Depends(get_validated_token_payload),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100000000, description="每页数量"),
    buildin: bool = Query(None,description="是否为内置模版过滤"),
    db: Session = Depends(get_sync_session)
):
    """
    获取算法模板列表，支持分页和条件查询
    
    Args:
        payload: 从token中解析的用户信息
        name: 模板名称（模糊查询）
        template_type: 模板类型过滤
        buildin: 是否为内置模版过滤
        page: 页码
        page_size: 每页数量
        db: 数据库会话
        
    Returns:
        Dict: 包含模板列表和分页信息的响应
    """
    try:
        user_id = payload.get("uuid")
        if not user_id:
            return response_fail(msg="Token中缺少用户信息 (uuid)")
        # 查询模板列表
        templates, total = get_templates_by_query(
            db, user_id, page, page_size, buildin
        )
        
        # 转换为响应模型
        template_responses = [AlgoTemplateResponse.model_validate(template) for template in templates]
        
        list_response = AlgoTemplateListResponse(
            templates=template_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
        return response_success(
            data=list_response,
            msg="查询成功"
        )
        
    except Exception as e:
        logger.error(f"查询算法模板列表失败: {e}")
        return response_fail(msg="查询失败")
    finally:
        db.close()


@router.get("/{template_id}", response_model=dict, summary="根据模板id获取单个算法模板详情")
async def get_algo_template_by_id(
    payload: Dict = Depends(get_validated_token_payload),
    template_id: int = Path(..., description="模板ID"),
    db: Session = Depends(get_sync_session)
):
    """
    根据模板ID获取单个算法模板
    
    Args:
        template_id: 模板ID
        payload: 从token中解析的用户信息
        db: 数据库会话
        
    Returns:
        Dict: 包含模板详情的响应
    """
    try:
        user_id = payload.get("uuid")
        if not user_id:
            return response_fail(msg="Token中缺少用户信息 (uuid)")

        # 查询模板
        template = get_template_by_id(db, template_id, user_id)
        
        if not template:
            return response_fail(msg="模板不存在或无权限访问")
        
        template_response = AlgoTemplateResponse.model_validate(template)
        
        return response_success(
            data=template_response,
            msg="查询成功"
        )
        
    except Exception as e:
        logger.error(f"查询算法模板详情失败: {e}")
        return response_fail(msg="查询失败")
    finally:
        db.close()


@router.post("/", response_model=dict, summary="创建新的算法模板")
async def create_algo_template(
    template_data: AlgoTemplateCreate,
    payload: Dict = Depends(get_validated_token_payload),
    db: Session = Depends(get_sync_session)
):
    """
    创建新的算法模板
    
    Args:
        payload: 从token中解析的用户信息
        template_data: 模板创建数据
        db: 数据库会话
        
    Returns:
        Dict: 包含创建结果的响应
    """
    try:
        user_id = payload.get("uuid")
        if not user_id:
            return response_fail(msg="Token中缺少用户信息 (uuid)")
            
        # 转换为字典格式
        template_dict = template_data.model_dump(exclude_none=True)
        
        # 设置用户user_id
        template_dict["user_id"] = user_id

        if find_repeat_name(db, template_data.name, user_id):
            return response_fail(msg="模板名称已存在")
        
        # 创建模板
        new_template = create_template(db, template_dict)
        
        template_response = AlgoTemplateResponse.model_validate(new_template)
        
        return response_success(
            data=template_response,
            msg="模板创建成功"
        )
        
    except Exception as e:
        logger.error(f"创建算法模板失败: {e}")
        return response_fail(msg="创建失败")
    finally:
        db.close()


@router.put("/{template_id}", response_model=dict, summary="更新算法模板")
async def update_algo_template(
    payload: Dict = Depends(get_validated_token_payload),
    template_id: int = Path(..., description="模板ID"),
    template_data: AlgoTemplateUpdate = None,
    db: Session = Depends(get_sync_session)
):
    """
    更新算法模板
    
    Args:
        payload: 从token中解析的用户信息
        template_id: 模板ID
        template_data: 模板更新数据
        db: 数据库会话
        
    Returns:
        Dict: 包含更新结果的响应
    """
    try:
        user_id = payload.get("uuid")
        if not user_id:
            return response_fail(msg="Token中缺少用户信息 (uuid)")

        # 先查询当前模板
        current_template = get_template_by_id(db, template_id, user_id)
        if not current_template:
            return response_fail(msg="模板不存在或无权限访问")

        # 如果 name 有变化，才检查重复
        if template_data.name and template_data.name != current_template.name:
            repeat_template = find_repeat_name(db, template_data.name, user_id)
            if repeat_template and repeat_template.id != template_id:
                return response_fail(msg="模板名称已存在")
        
        # 转换为字典格式，排除None值和id字段
        template_dict = template_data.model_dump(exclude_none=True, exclude={"id","user_id"})
        
        # 更新模板
        updated_template = update_template_by_id(db, template_id, user_id, template_dict)
        
        if not updated_template:
            return response_fail(msg="模板不存在或无权限访问")
        
        template_response = AlgoTemplateResponse.model_validate(updated_template)
        
        return response_success(
            data=template_response,
            msg="模板更新成功"
        )
        
    except Exception as e:
        logger.error(f"更新算法模板失败: {e}")
        return response_fail(msg="更新失败")
    finally:
        db.close()


@router.delete("/{template_id}", response_model=dict, summary="删除算法模板")
async def delete_algo_template(
    payload: Dict = Depends(get_validated_token_payload),
    template_id: int = Path(..., description="模板ID"),
    db: Session = Depends(get_sync_session)
):
    """
    删除算法模板
    
    Args:
        payload: 从token中解析的用户信息
        template_id: 模板ID
        db: 数据库会话
        
    Returns:
        Dict: 包含删除结果的响应
    """
    try:
        user_id = payload.get("uuid")
        if not user_id:
            return response_fail(msg="Token中缺少用户信息 (uuid)")

        # 删除模板
        success = delete_template_by_id(db, template_id, user_id)
        
        if not success:
            return response_fail(msg="模板不存在或无权限访问")
        
        return response_success(
            data={"template_id": template_id},
            msg="模板删除成功"
        )
        
    except Exception as e:
        logger.error(f"删除算法模板失败: {e}")
        return response_fail(msg="删除失败")
    finally:
        db.close()

@router.get("/type/getType", summary="获取算法模版分类")
async def get_algo_template_type():
    """
    获取算法模版分类

    Returns:
        Dict: 响应数据
    """

    template_type = {"data_refine","data_enhancement","data_generation"}

    return response_success(
        data=template_type,
        msg="获取算法模版分类成功"
    )

@router.get("/get/ByName", response_model=dict, summary="根据模版名称获取算法模板列表")
async def get_algo_template_by_name(
    payload: Dict = Depends(get_validated_token_payload),
    template_name: str = Query(..., description="模板名称"),
    db: Session = Depends(get_sync_session)
):
    """
    根据模版名称获取算法模板列表

    Args:
        payload: 从token中解析的用户信息
        template_name: 模板名称
        db: 数据库会话

    Returns:
        Dict: 获取算法模板列表的响应
    """
    try:
        user_id = payload.get("uuid")
        if not user_id:
            return response_fail(msg="Token中缺少用户信息 (uuid)")

        # 查询模板
        template = find_repeat_name(db, template_name, user_id)
        
        if not template:
            return response_fail(msg="模板不存在或无权限访问")
        
        template_response = AlgoTemplateResponse.model_validate(template)
        
        return response_success(
            data=template_response,
            msg="查询成功"
        )
        
    except Exception as e:
        logger.error(f"根据名称查询算法模板失败: {e}")
        return response_fail(msg="查询失败")
    finally:
        db.close()
