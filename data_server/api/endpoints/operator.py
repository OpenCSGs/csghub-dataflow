from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Annotated

from data_server.database.session import get_sync_session
# 导入你的模型和数据访问函数
from data_server.operator.mapper.operator_mapper import (
    get_operator, get_operators, create_operator, update_operator, delete_operator,
    get_operator_config_select_options_list, get_operator_config_select_option_by_id,
    create_operator_config_select_option, get_operators_grouped_by_type, get_operators_grouped_by_condition
)
from data_server.operator.schemas import (
    OperatorCreateRequest, OperatorUpdateRequest, OperatorConfigSelectOptionsCreate,
    OperatorResponse, OperatorConfigSelectOptionsResponse
)
from ...schemas.responses import response_success, response_fail
from ...api.dependencies import get_validated_token_payload

app = FastAPI(title="operator-API")
router = APIRouter()

# 算子相关API
# 创建算子
@router.post("/", summary="create_operator")
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
@router.get("/", summary="GET_LIST_OF_OPERATORS")
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
@router.get("/{operator_id}", summary="obtain the operator based on the id")
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
@router.put("/{operator_id}", summary="updateOperator")
def update_operator_api(
    operator_id: int,
    operator_data: OperatorUpdateRequest,
    db: Session = Depends(get_sync_session)
):
    """
    更新指定ID的算子信息
    
    ## 参数说明
    - **operator_id**:
    - **operator_data**:
      - operator_name:
      - operator_type:
      - execution_order:
      - is_enabled:
      - description:
      - before_cleaning:
      - after_cleaning:
      - icon:
      - configs:
    - **user_id**:
    """
    try:
        db_operator = update_operator(db, operator_id, operator_data.model_dump(exclude_unset=True))
        if db_operator is None:
            return response_fail(msg="算子不存在")
        return response_success(data=db_operator, msg="更新算子成功")
    except Exception as e:
        return response_fail(msg=f"更新算子失败: {str(e)}")
    finally:
        db.close()

# 删除算子
@router.delete("/{operator_id}", summary="deletionOperator")
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
@router.get("/config_select_options/{option_id}", summary="obtain_the_record_based_on_the_primary_key_id")
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
@router.post("/config_select_options/", summary="添加下拉框选项")
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


@router.get("/types/grouped-by-type", summary="根据算子分类返回算子数据")
def get_operators_grouped_by_type_api(
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
        grouped_operators = get_operators_grouped_by_type(db)
        return response_success(data=grouped_operators, msg="获取分组算子列表成功")
    except Exception as e:
        return response_fail(msg=f"获取分组算子列表失败: {str(e)}")
    finally:
        db.close()

# find_operator_by_uuid_orgs
@router.get("/types/grouped-by-condition/", summary="根据算子分类和权限返回算子数据")
def get_operators_grouped_by_condition_api(
    payload: Dict = Depends(get_validated_token_payload),
    db: Session = Depends(get_sync_session),
    full_path: Optional[str] = Query(default=None, description="当前用户对应的组织名称, 多个用逗号隔开")
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
        # 获取所有path信息
        if full_path:
            paths: List[str] = full_path.split(',')
        else:
            paths = []

        user_id = payload.get("uuid")
        if not user_id:
            return response_fail("Token中缺少用户信息 (uuid)")

        grouped_operators = get_operators_grouped_by_condition(db, user_id, paths)
        return response_success(data=grouped_operators, msg="获取分组算子列表成功")
    except Exception as e:
        return response_fail(msg=f"获取分组算子列表失败: {str(e)}")
    finally:
        db.close()
