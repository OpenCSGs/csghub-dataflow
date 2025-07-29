from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Union

from data_server.database.session import get_sync_session
from data_server.operator.mapper.operator_permission_mapper import (
    get_operator_permission, get_operator_permissions, get_permissions_by_operator,
    get_permissions_by_user, get_permissions_by_role_type,
    create_operator_permission, update_operator_permission,
    delete_operator_permission, delete_permissions_by_operator, delete_permissions_by_user
)
from data_server.operator.schemas import OperatorPermissionResponse
from data_server.schemas.responses import response_success, response_fail

router = APIRouter()


# 创建算子权限
@router.post("/",summary="创建算子权限")
def create_permission_api(permission_data: Dict[str, Any], db: Session = Depends(get_sync_session)):
    """
    创建新的算子权限记录，支持批量授权

    ## 参数说明
    - **permission_data**: 权限数据，格式如下:
      {
        "operator_id": 算子ID,
        "role_type": "角色类型",
        "list": [
          {
            "uuid": "用户UUID",
            "username": "用户名" (可选)
          },
          ...
        ]
      }

    ## 返回值
    - 创建成功：返回新创建的权限记录列表
    - 创建失败：返回错误信息
    """
    try:
        # 验证请求数据格式
        if "operator_id" not in permission_data or "list" not in permission_data or "role_type" not in permission_data:
            return response_fail(msg="请求数据格式错误，需要包含 operator_id、role_type 和 list 字段")

        operator_id = permission_data["operator_id"]
        role_type = permission_data["role_type"]
        user_list = permission_data["list"]

        if not isinstance(user_list, list) or len(user_list) == 0:
            return response_fail(msg="用户列表不能为空")

        # 检查数据库中已存在的权限记录，过滤掉重复的
        from data_server.operator.mapper.operator_permission_mapper import get_permissions_by_operator
        existing_permissions = get_permissions_by_operator(db, operator_id)
        existing_uuids = {perm.uuid for perm in existing_permissions}

        # 过滤出需要插入的新记录（排除已存在的）
        new_users = []
        skipped_uuids = []

        for user_data in user_list:
            uuid = user_data["uuid"]
            if uuid in existing_uuids:
                skipped_uuids.append(uuid)
            else:
                new_users.append(user_data)

        # 如果没有新用户需要插入
        if not new_users:
            return response_success(
                data=[],
                msg=f"所选用户都已拥有该算子权限"
            )

        # 构造批量插入数据（只包含新用户）
        batch_data = []
        for user_data in new_users:
            permission_record = {
                "operator_id": operator_id,
                "uuid": user_data["uuid"],
                "role_type": role_type,
                "username": user_data.get("username")
            }
            batch_data.append(permission_record)

        # 调用批量创建函数
        result = create_operator_permission(db, batch_data)

        # 构造返回消息
        if skipped_uuids:
            msg = f"批量创建算子权限成功，共创建 {len(result)} 条记录，跳过 {len(skipped_uuids)} 个已存在的用户"
        else:
            msg = f"批量创建算子权限成功，共创建 {len(result)} 条记录"

        return response_success(data=result, msg=msg)
    except Exception as e:
        return response_fail(msg=f"算子权限创建失败: {str(e)}")

# 获取权限列表
@router.get("/", summary="获取权限列表")
def read_permissions_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_sync_session)):
    """
    获取所有算子权限列表
    
    ## 参数说明
    - **skip**: 分页参数，跳过的记录数
    - **limit**: 分页参数，返回的最大记录数
    
    ## 返回值
    - 查询成功：返回权限记录列表
    - 查询失败：返回错误信息
    """
    try:
        permissions = get_operator_permissions(db, skip, limit)
        return response_success(data=permissions, msg="获取权限列表成功")
    except Exception as e:
        return response_fail(msg=f"获取权限列表失败: {str(e)}")

# 获取单个权限
@router.get("/{permission_id}", summary="根据主键获取单个权限")
def read_permission_api(permission_id: int, db: Session = Depends(get_sync_session)):
    """
    根据ID获取单个权限记录
    
    ## 参数说明
    - **permission_id**: 权限记录的唯一标识ID
    
    ## 返回值
    - 查询成功：返回权限记录详情
    - 权限不存在：返回"权限不存在"错误
    - 查询失败：返回错误信息
    """
    try:
        permission = get_operator_permission(db, permission_id)
        if permission is None:
            return response_fail(msg="权限不存在")
        return response_success(data=permission, msg="获取权限成功")
    except Exception as e:
        return response_fail(msg=f"获取权限失败: {str(e)}")

# 获取指定算子的所有权限
@router.get("/operator/{operator_id}", summary="根据算子id查询有权限的用户列表")
def read_permissions_by_operator_api(operator_id: int, db: Session = Depends(get_sync_session)):
    """
    获取指定算子的所有权限记录
    
    ## 参数说明
    - **operator_id**: 算子的唯一标识ID
    
    ## 返回值
    - 查询成功：返回与该算子相关的所有权限记录
    - 查询失败：返回错误信息
    """
    try:
        permissions = get_permissions_by_operator(db, operator_id)
        return response_success(data=permissions, msg="获取算子权限成功")
    except Exception as e:
        return response_fail(msg=f"获取算子权限失败: {str(e)}")


# 获取指定用户的所有权限
@router.get("/user/{uuid}", summary="根据用户id查询有权限的算子列表")
def read_permissions_by_user_api(uuid: str, db: Session = Depends(get_sync_session)):
    """
    获取指定用户的所有权限记录

    ## 参数说明
    - **uuid**: 用户的唯一标识符

    ## 返回值
    - 查询成功：返回与该用户相关的所有权限记录
    - 查询失败：返回错误信息
    """
    try:
        permissions = get_permissions_by_user(db, uuid)
        return response_success(data=permissions, msg="获取用户权限成功")
    except Exception as e:
        return response_fail(msg=f"获取用户权限失败: {str(e)}")

# 获取指定角色类型的所有权限
@router.get("/role-type/{role_type}", summary="根据角色类型查询有权限的算子列表")
def read_permissions_by_role_type_api(role_type: int, db: Session = Depends(get_sync_session)):
    """
    获取指定角色类型的所有权限记录
    
    ## 参数说明
    - **role_type**: 角色类型
    
    ## 返回值
    - 查询成功：返回与该角色类型相关的所有权限记录
    - 查询失败：返回错误信息
    """
    try:
        permissions = get_permissions_by_role_type(db, role_type)
        return response_success(data=permissions, msg="获取角色类型权限成功")
    except Exception as e:
        return response_fail(msg=f"获取角色类型权限失败: {str(e)}")

# 更新权限
@router.put("/{permission_id}", summary="更新权限")
def update_permission_api(permission_id: int, permission_data: Dict[str, Any], db: Session = Depends(get_sync_session)):
    """
    更新指定ID的权限记录

    ## 参数说明
    - **permission_id**: 权限记录的唯一标识ID
    - **permission_data**: 权限更新数据，可包含以下字段:
      - operator_id: 算子ID
      - uuid: 用户UUID
      - role_type: 角色类型
      - username: 用户名

    ## 返回值
    - 更新成功：返回更新后的权限记录
    - 权限不存在：返回"权限不存在"错误
    - 更新失败：返回错误信息
    """
    try:
        permission = update_operator_permission(db, permission_id, permission_data)
        if permission is None:
            return response_fail(msg="权限不存在")
        return response_success(data=permission, msg="更新权限成功")
    except Exception as e:
        return response_fail(msg=f"更新权限失败: {str(e)}")

# 删除权限
@router.delete("/{permission_id}", summary="删除权限")
def delete_permission_api(permission_id: int, db: Session = Depends(get_sync_session)):
    """
    删除指定ID的权限记录
    
    ## 参数说明
    - **permission_id**: 权限记录的唯一标识ID
    
    ## 返回值
    - 删除成功：返回成功消息
    - 权限不存在：返回"权限不存在"错误
    - 删除失败：返回错误信息
    """
    try:
        success = delete_operator_permission(db, permission_id)
        if not success:
            return response_fail(msg="权限不存在")
        return response_success(msg="删除权限成功")
    except Exception as e:
        return response_fail(msg=f"删除权限失败: {str(e)}")

# 删除指定算子的所有权限
@router.delete("/operator/{operator_id}", summary="删除指定算子的所有人权限")
def delete_permissions_by_operator_api(operator_id: int, db: Session = Depends(get_sync_session)):
    """
    删除指定算子的所有权限记录
    
    ## 参数说明
    - **operator_id**: 算子的唯一标识ID
    
    ## 返回值
    - 删除成功：返回删除的记录数量
    - 删除失败：返回错误信息
    """
    try:
        count = delete_permissions_by_operator(db, operator_id)
        return response_success(data={"deleted_count": count}, msg=f"成功删除 {count} 条权限记录")
    except Exception as e:
        return response_fail(msg=f"删除算子权限失败: {str(e)}")

# 删除指定用户的所有权限
@router.delete("/user/{uuid}", summary="删除指定用户的所有权限")
def delete_permissions_by_user_api(uuid: str, db: Session = Depends(get_sync_session)):
    """
    删除指定用户的所有权限记录

    ## 参数说明
    - **uuid**: 用户的唯一标识符

    ## 返回值
    - 删除成功：返回删除的记录数量
    - 删除失败：返回错误信息
    """
    try:
        count = delete_permissions_by_user(db, uuid)
        return response_success(data={"deleted_count": count}, msg=f"成功删除 {count} 条权限记录")
    except Exception as e:
        return response_fail(msg=f"删除用户权限失败: {str(e)}")