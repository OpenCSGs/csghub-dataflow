from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query,Path,Header
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional,Annotated

from data_server.database.session import get_sync_session
# 导入你的模型和数据访问函数
from data_server.operator.mapper.operator_mapper import (
    get_operator, get_operators, create_operator, update_operator, delete_operator, get_operator_config_select_options_list, get_operator_config_select_option_by_id, create_operator_config_select_option, get_operators_grouped_by_type
)
from data_server.operator.schemas import (
    OperatorCreateRequest, OperatorUpdateRequest, OperatorConfigSelectOptionsCreate,
    OperatorResponse, OperatorConfigSelectOptionsResponse
)
from ...schemas.responses import response_success, response_fail
from ...utils.jwt_utils import parse_jwt_token

app = FastAPI(title="算子管理API")
router = APIRouter()

# 算子相关API
# 创建算子
@router.post("/",summary="创建算子")
def create_operator_api(
    operator_data: OperatorCreateRequest,
    db: Session = Depends(get_sync_session)
):
    """
    创建新的算子

    ## 参数说明
    - **operator_data**: 算子创建数据，包含以下字段:
      - operator_name: 算子名称 (必填)
      - operator_type: 算子类型 (必填)
      - execution_order: 执行顺序 (可选，默认0)
      - is_enabled: 是否启用 (可选，默认true)
      - description: 描述信息 (可选)
      - before_cleaning: 清洗前数据说明 (可选)
      - after_cleaning: 清洗后数据说明 (可选)
      - icon: 图标 (可选)
      - configs: 算子配置列表 (可选)

    ## 返回值
    - 创建成功：返回新创建的算子信息
    - 创建失败：返回错误信息
    """
    try:
        result = create_operator(db, operator_data.model_dump())
        return response_success(data=result, msg="算子创建成功")
    except Exception as e:
        return response_fail(msg=f"算子创建失败: {str(e)}")
    finally:
        db.close()

# 获取算子列表
@router.get("/",summary="获取算子列表")
def read_operators_api(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_sync_session)
):
    """
    获取算子列表
    
    ## 参数说明
    - **skip**: 分页参数，跳过的记录数
    - **limit**: 分页参数，返回的最大记录数
    
    ## 返回值
    - 查询成功：返回算子列表
    - 查询失败：返回错误信息
    """
    try:
        operators = get_operators(db, skip, limit)
        return response_success(data=operators, msg="获取算子列表成功")
    except Exception as e:
        return response_fail(msg=f"获取算子列表失败: {str(e)}")
    finally:
        db.close()

# 获取单个算子
@router.get("/{operator_id}",summary="根据id获取算子")
def read_operator_api(
    operator_id: int = Path(description="算子ID"),
    db: Session = Depends(get_sync_session)
):
    """
    根据ID获取单个算子详情
    
    ## 参数说明
    - **operator_id**: 算子的唯一标识ID
    
    ## 返回值
    - 查询成功：返回算子详情
    - 算子不存在：返回"算子不存在"错误
    - 查询失败：返回错误信息
    """
    try:
        db_operator = get_operator(db, operator_id)
        if db_operator is None:
            return response_fail(msg="算子不存在")
        return response_success(data=db_operator, msg="获取算子成功")
    except Exception as e:
        return response_fail(msg=f"获取算子失败: {str(e)}")
    finally:
        db.close()

# 更新算子
@router.put("/{operator_id}",summary="更新算子")
def update_operator_api(
    operator_id: int,
    operator_data: OperatorUpdateRequest,
    db: Session = Depends(get_sync_session)
):
    """
    更新指定ID的算子信息
    
    ## 参数说明
    - **operator_id**: 算子的唯一标识ID
    - **operator_data**: 算子更新数据，可包含以下字段:
      - operator_name: 算子名称 (可选)
      - operator_type: 算子类型 (可选)
      - execution_order: 执行顺序 (可选)
      - is_enabled: 是否启用 (可选)
      - description: 描述信息 (可选)
      - before_cleaning: 清洗前数据说明 (可选)
      - after_cleaning: 清洗后数据说明 (可选)
      - icon: 图标 (可选)
      - configs: 算子配置列表 (可选)
    - **user_id**: 执行更新操作的用户ID

    ## 返回值
    - 更新成功：返回更新后的算子信息
    - 算子不存在：返回"算子不存在"错误
    - 更新失败：返回错误信息
    """
    try:
        # 检查更新权限
        # if not check_update_permission(db, user_id, operator_id):
        #     return response_fail(msg="没有修改该算子的权限")
            
        db_operator = update_operator(db, operator_id, operator_data.model_dump(exclude_unset=True))
        if db_operator is None:
            return response_fail(msg="算子不存在")
        return response_success(data=db_operator, msg="更新算子成功")
    except Exception as e:
        return response_fail(msg=f"更新算子失败: {str(e)}")
    finally:
        db.close()

# 删除算子
@router.delete("/{operator_id}",summary="删除算子")
def delete_operator_api(
    operator_id: int,
    user_id: int = Query(None, description="用户ID"),
    db: Session = Depends(get_sync_session)
):
    """
    删除指定ID的算子

    ## 参数说明
    - **operator_id**: 算子的唯一标识ID
    - **user_id**: 执行删除操作的用户ID

    ## 返回值
    - 删除成功：返回成功消息
    - 算子不存在：返回"算子不存在"错误
    - 删除失败：返回错误信息
    """
    try:
        # 检查删除权限
        # if not check_delete_permission(db, user_id, operator_id):
        #     return response_fail(msg="没有删除该算子的权限")
            
        success = delete_operator(db, operator_id)
        if not success:
            return response_fail(msg="算子不存在")
        return response_success(msg="删除算子成功")
    except Exception as e:
        return response_fail(msg=f"删除算子失败: {str(e)}")
    finally:
        db.close()

# 根据id获取operator_config_select_options单条记录
@router.get("/config_select_options/{option_id}",summary="根据主键id获取记录")
def get_operator_config_select_option_by_id_api(
    option_id: int,
    db: Session = Depends(get_sync_session)
):
    """
    根据id获取operator_config_select_options单条记录
    """
    try:
        option = get_operator_config_select_option_by_id(db, option_id)
        if not option:
            return response_fail(msg="选项不存在")
        return response_success(data=option, msg="获取选项成功")
    except Exception as e:
        return response_fail(msg=f"获取选项失败: {str(e)}")
    finally:
        db.close()

# 新增：添加operator_config_select_options表记录
@router.post("/config_select_options/",summary="添加下拉框选项")
def create_operator_config_select_option_api(
    option: OperatorConfigSelectOptionsCreate,
    db: Session = Depends(get_sync_session)
):
    """
    添加operator_config_select_options表记录
    """
    try:
        result = create_operator_config_select_option(db, option.model_dump())
        return response_success(data=result, msg="添加下拉选项成功")
    except Exception as e:
        return response_fail(msg=f"添加下拉选项失败: {str(e)}")
    finally:
        db.close()

# 新增：根据operator_type分类返回算子数据
@router.get("/types/grouped-by-type",summary="根据算子分类返回算子数据")
def get_operators_grouped_by_type_api(
    authorization: Annotated[str, Header(alias="Authorization")],
    db: Session = Depends(get_sync_session)
):
    """
    根据operator_type分类返回算子数据

    ## 返回值格式
    ```json
    [
        {
            "typeName": "Mapper",
            "list": [对应mapper的operator_info的列表]
        },
        {
            "typeName": "Filter",
            "list": []
        },
        {
            "typeName": "Deduplicator",
            "list": []
        },
        {
            "typeName": "Selector",
            "list": []
        },
        {
            "typeName": "Formatter",
            "list": []
        }
    ]
    ```

    ## 返回值
    - 查询成功：返回按类型分组的算子列表
    - 查询失败：返回错误信息
    """
    try:
        # 从JWT token中提取user_id
        token_info = parse_jwt_token(authorization)

        # 检查token是否过期
        if token_info["is_expired"]:
            return response_fail("Token已经过期")
        # 获取用户user_id
        uuid = token_info["payload"].get("uuid")
        grouped_operators = get_operators_grouped_by_type(db,uuid)
        return response_success(data=grouped_operators, msg="获取分组算子列表成功")
    except Exception as e:
        return response_fail(msg=f"获取分组算子列表失败: {str(e)}")
    finally:
        db.close()