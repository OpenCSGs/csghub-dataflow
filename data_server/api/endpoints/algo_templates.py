from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Header
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Annotated
from loguru import logger
from pydantic import BaseModel, Field

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

    templates: List[AlgoTemplateResponse] = Field(..., description="算法模板列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


@router.get("", response_model=dict, summary="获取算法模板列表")
async def get_algo_templates(
    user_id: str = Header(..., alias="user_id", description="用户ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100000000, description="每页数量"),
    buildin: bool = Query(None,description="是否为内置模版过滤"),
    db: Session = Depends(get_sync_session)
):

    try:
        if not user_id:
            return response_fail(msg="请求头中缺少用户信息 (user_id)")

        templates, total = get_templates_by_query(
            db, user_id, page, page_size, buildin
        )
        

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
    user_id: str = Header(..., alias="user_id", description="用户ID"),
    template_id: int = Path(..., description="模板ID"),
    db: Session = Depends(get_sync_session)
):

    try:
        if not user_id:
            return response_fail(msg="请求头中缺少用户信息 (user_id)")


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


@router.post("", response_model=dict, summary="创建新的算法模板")
async def create_algo_template(
    template_data: AlgoTemplateCreate,
    user_id: str = Header(..., alias="user_id", description="用户ID"),
    db: Session = Depends(get_sync_session)
):

    try:
        if not user_id:
            return response_fail(msg="请求头中缺少用户信息 (user_id)")
            

        template_dict = template_data.model_dump(exclude_none=True)
        

        template_dict["user_id"] = user_id

        if find_repeat_name(db, template_data.name, user_id):
            return response_fail(msg="模板名称已存在")
        

        new_template = create_template(db, template_dict)
        
        template_response = AlgoTemplateResponse.model_validate(new_template)
        
        return response_success(
            data=template_response,
            msg="模板创建成功"
        )
        
    except Exception as e:
        logger.error(f"创建算法模板失败: {e}")
        return response_fail(msg="创建模版失败:" + str(e))
    finally:
        db.close()


@router.put("/{template_id}", response_model=dict, summary="更新算法模板")
async def update_algo_template(
    user_id: str = Header(..., alias="user_id", description="用户ID"),
    template_id: int = Path(..., description="模板ID"),
    template_data: AlgoTemplateUpdate = None,
    db: Session = Depends(get_sync_session)
):

    try:
        if not user_id:
            return response_fail(msg="请求头中缺少用户信息 (user_id)")


        current_template = get_template_by_id(db, template_id, user_id)
        if not current_template:
            return response_fail(msg="模板不存在或无权限访问")


        if template_data.name and template_data.name != current_template.name:
            repeat_template = find_repeat_name(db, template_data.name, user_id)
            if repeat_template and repeat_template.id != template_id:
                return response_fail(msg="模板名称已存在")
        

        template_dict = template_data.model_dump(exclude_none=True, exclude={"id","user_id"})
        

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
        return response_fail(msg="算法更新失败:" + str(e))
    finally:
        db.close()


@router.delete("/{template_id}", response_model=dict, summary="删除算法模板")
async def delete_algo_template(
    user_id: str = Header(..., alias="user_id", description="用户ID"),
    template_id: int = Path(..., description="模板ID"),
    db: Session = Depends(get_sync_session)
):

    try:
        if not user_id:
            return response_fail(msg="请求头中缺少用户信息 (user_id)")


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


    template_type = {"data_refine","data_enhancement","data_generation"}

    return response_success(
        data=template_type,
        msg="获取算法模版分类成功"
    )

@router.get("/get/ByName", response_model=dict, summary="根据模版名称获取算法模板列表")
async def get_algo_template_by_name(
    user_id: str = Header(..., alias="user_id", description="用户ID"),
    template_name: str = Query(..., description="模板名称"),
    db: Session = Depends(get_sync_session)
):

    try:
        if not user_id:
            return response_fail(msg="请求头中缺少用户信息 (user_id)")


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
