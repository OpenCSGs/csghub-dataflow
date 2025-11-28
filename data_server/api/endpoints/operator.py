from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, Path as FPath, Header, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Annotated
import base64
import os
from pathlib import Path
from loguru import logger
from data_celery.utils import get_project_root

from data_server.database.session import get_sync_session

from data_server.operator.mapper.operator_mapper import (
    get_operator, get_operators, create_operator, update_operator, delete_operator,
    get_operator_config_select_options_list, get_operator_config_select_option_by_id,
    create_operator_config_select_option, get_operators_grouped_by_type, get_operators_grouped_by_condition
)
from data_server.operator.models.operator import OperatorInfo
from data_server.operator.schemas import (
    OperatorCreateRequest, OperatorUpdateRequest, OperatorConfigSelectOptionsCreate,
    OperatorResponse, OperatorConfigSelectOptionsResponse, OperatorDocumentResponse
)
from ...schemas.responses import response_success, response_fail
from ...api.dependencies import get_validated_token_payload

app = FastAPI(title="operator-API")
router = APIRouter()



@router.post("", summary="create_operator")
def create_operator_api(
    operator_data: OperatorCreateRequest,
    db: Session = Depends(get_sync_session)
):

    try:
        result = create_operator(db, operator_data.model_dump())
        return response_success(data=result, msg="算子创建成功")
    except Exception as e:
        return response_fail(msg=f"算子创建失败: {str(e)}")
    finally:
        db.close()


@router.get("", summary="GET_LIST_OF_OPERATORS")
def read_operators_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_sync_session)
):

    try:
        operators = get_operators(db, skip, limit)
        operators_data = []
        project_root = get_project_root()
        for op in operators:
            op_dict = op.__dict__
            pic_base64 = None
            mime_type = None
            if op.icon:
                try:
                    filename = Path(op.icon).name
                    image_path = project_root / 'attach' / 'operator' / filename
                    if image_path.exists() and image_path.is_file():
                        with open(image_path, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                        pic_base64 = encoded_string
                except Exception:
                    # Ignore errors for individual images
                    pass
            op_dict['pic_base64'] = pic_base64
            operators_data.append(op_dict)

        operators_data.sort(key=lambda x: x['id'])
        return response_success(data=operators_data, msg="获取算子列表成功")
    except Exception as e:
        return response_fail(msg=f"获取算子列表失败: {str(e)}")
    finally:
        db.close()


@router.get("/{operator_id}", summary="obtain the operator based on the id")
def read_operator_api(
    operator_id: int = FPath(description="算子ID"),
    db: Session = Depends(get_sync_session)
):

    try:
        db_operator = get_operator(db, operator_id)
        if db_operator is None:
            return response_fail(msg="算子不存在")
        return response_success(data=db_operator, msg="获取算子成功")
    except Exception as e:
        return response_fail(msg=f"获取算子失败: {str(e)}")
    finally:
        db.close()


@router.put("/{operator_id}", summary="updateOperator")
def update_operator_api(
    operator_id: int,
    operator_data: OperatorUpdateRequest,
    db: Session = Depends(get_sync_session)
):

    try:
        db_operator = update_operator(db, operator_id, operator_data.model_dump(exclude_unset=True))
        if db_operator is None:
            return response_fail(msg="算子不存在")
        return response_success(data=db_operator, msg="更新算子成功")
    except Exception as e:
        return response_fail(msg=f"更新算子失败: {str(e)}")
    finally:
        db.close()


@router.delete("/{operator_id}", summary="deletionOperator")
def delete_operator_api(
    operator_id: int,
    user_id: int = Query(None, description="用户ID"),
    db: Session = Depends(get_sync_session)
):

    try:

        # if not check_delete_permission(db, user_id, operator_id):

            
        success = delete_operator(db, operator_id)
        if not success:
            return response_fail(msg="算子不存在")
        return response_success(msg="删除算子成功")
    except Exception as e:
        return response_fail(msg=f"删除算子失败: {str(e)}")
    finally:
        db.close()


@router.get("/config_select_options/{option_id}", summary="obtain_the_record_based_on_the_primary_key_id")
def get_operator_config_select_option_by_id_api(
    option_id: int,
    db: Session = Depends(get_sync_session)
):

    try:
        option = get_operator_config_select_option_by_id(db, option_id)
        if not option:
            return response_fail(msg="选项不存在")
        return response_success(data=option, msg="获取选项成功")
    except Exception as e:
        return response_fail(msg=f"获取选项失败: {str(e)}")
    finally:
        db.close()


@router.post("/config_select_options", summary="添加下拉框选项")
def create_operator_config_select_option_api(
    option: OperatorConfigSelectOptionsCreate,
    db: Session = Depends(get_sync_session)
):

    try:
        result = create_operator_config_select_option(db, option.model_dump())
        return response_success(data=result, msg="添加下拉选项成功")
    except Exception as e:
        return response_fail(msg=f"添加下拉选项失败: {str(e)}")
    finally:
        db.close()


@router.get("/types/grouped-by-type", summary="根据算子分类返回算子数据")
def get_operators_grouped_by_type_api(
    db: Session = Depends(get_sync_session)
):

    try:
        grouped_operators = get_operators_grouped_by_type(db)
        project_root = get_project_root()
        for group in grouped_operators:
            for op in group['list']:
                pic_base64 = None
                icon = op.get('icon')
                if icon:
                    try:
                        filename = Path(icon).name
                        image_path = project_root / 'attach' / 'operator' / filename
                        if image_path.exists() and image_path.is_file():
                            with open(image_path, "rb") as image_file:
                                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                            pic_base64 = encoded_string
                    except Exception:
                        pass
                op['pic_base64'] = pic_base64
        return response_success(data=grouped_operators, msg="获取分组算子列表成功")
    except Exception as e:
        return response_fail(msg=f"获取分组算子列表失败: {str(e)}")
    finally:
        db.close()

# find_operator_by_uuid_orgs
@router.get("/types/grouped-by-condition", summary="根据算子分类和权限返回算子数据")
def get_operators_grouped_by_condition_api(
    payload: Dict = Depends(get_validated_token_payload),
    db: Session = Depends(get_sync_session),
    full_path: Optional[str] = Query(default=None, description="当前用户对应的组织名称, 多个用逗号隔开")
):

    try:

        if full_path:
            paths: List[str] = full_path.split(',')
        else:
            paths = []

        user_id = payload.get("uuid")
        if not user_id:
            return response_fail("Token中缺少用户信息 (uuid)")

        grouped_operators = get_operators_grouped_by_condition(db, user_id, paths)
        project_root = get_project_root()
        for group in grouped_operators:
            for op in group['list']:
                pic_base64 = None
                icon = op.get('icon')
                if icon:
                    try:
                        filename = Path(icon).name
                        image_path = project_root / 'attach' / 'operator' / filename
                        if image_path.exists() and image_path.is_file():
                            with open(image_path, "rb") as image_file:
                                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                            pic_base64 = encoded_string
                    except Exception:
                        pass
                op['pic_base64'] = pic_base64
        return response_success(data=grouped_operators, msg="获取分组算子列表成功")
    except Exception as e:
        return response_fail(msg=f"获取分组算子列表失败: {str(e)}")
    finally:
        db.close()

@router.get("/isAdmin/torf")
def get_isAdmin_true_or_false(isadmin: str = Header(..., alias="isadmin", description="是否管理员")):
    if isadmin == "false":
        isadmin = False
    else:
        isadmin = True
    return response_success(data={"isadmin":isadmin})


# ==================== Operator Document Related APIs ====================

@router.post("/{operator_id}/document", summary="上传算子文档")
async def upload_operator_document_api(
    operator_id: int = FPath(..., description="算子ID"),
    file: UploadFile = File(..., description="Markdown文档文件"),
    db: Session = Depends(get_sync_session)
):
    """Upload operator document: save md file to file system"""
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith('.md'):
            return response_fail(msg="仅支持 .md 格式文件")
        
        # Check if operator exists and get operator name
        operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
        if not operator:
            return response_fail(msg="算子不存在")
        
        if not operator.operator_name:
            return response_fail(msg="算子名称不存在")
        
        # Read file content
        content_bytes = await file.read()
        content_str = content_bytes.decode('utf-8')
        
        # Validate content is not empty
        if not content_str.strip():
            return response_fail(msg="文档内容不能为空")
        
        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content_bytes) > max_size:
            return response_fail(msg=f"文档大小不能超过 {max_size // (1024 * 1024)}MB")
        
        # Get document save path
        project_root = get_project_root()
        operator_docs_dir = Path(project_root) / 'attach' / 'operator_docs'
        operator_docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file with operator name as filename
        file_path = operator_docs_dir / f"{operator.operator_name}.md"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content_str)
        
        logger.info(f"算子 {operator_id} ({operator.operator_name}) 的文档已保存到: {file_path}")
        
        return response_success(
            data={
                "operator_id": operator_id,
                "operator_name": operator.operator_name,
                "content": content_str
            },
            msg="文档上传成功"
        )
    except UnicodeDecodeError:
        return response_fail(msg="文件编码错误，请使用 UTF-8 编码")
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        return response_fail(msg=f"文档上传失败: {str(e)}")
    finally:
        db.close()


@router.get("/{operator_id}/document", summary="查询算子文档")
def get_operator_document_api(
    operator_id: int = FPath(..., description="算子ID"),
    db: Session = Depends(get_sync_session)
):
    """Get operator document content (read from file system)"""
    try:
        # Check if operator exists and get operator name
        operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
        if not operator:
            return response_fail(msg="算子不存在")
        
        if not operator.operator_name:
            return response_fail(msg="算子名称不存在")
        
        # Get document path
        project_root = get_project_root()
        file_path = Path(project_root) / 'attach' / 'operator_docs' / f"{operator.operator_name}.md"
        
        # Check if file exists
        if not file_path.exists():
            return response_fail(msg="文档不存在")
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return response_success(
            data={
                "operator_id": operator_id,
                "operator_name": operator.operator_name,
                "content": content
            },
            msg="获取文档成功"
        )
    except Exception as e:
        logger.error(f"获取文档失败: {str(e)}")
        return response_fail(msg=f"获取文档失败: {str(e)}")
    finally:
        db.close()