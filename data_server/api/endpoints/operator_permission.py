from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from data_server.database.session import get_sync_session
from data_server.operator.mapper.operator_permission_mapper import (
    create_operator_permission, delete_operator_permission,
    delete_permissions_by_operator, delete_permissions_by_user,
    get_operator_permission, get_operator_permissions,
    get_permissions_by_operator, get_permissions_by_role_type,
    get_permissions_by_user, update_operator_permission, delete_permissions_by_path)
from data_server.operator.schemas import OperatorPermissionCreateRequest
from data_server.schemas.responses import response_fail, response_success

router = APIRouter()


# 创建算子权限
@router.post("/", summary="创建算子权限")
def create_permission_api(request_data: OperatorPermissionCreateRequest, db: Session = Depends(get_sync_session)):
    """
    创建新的算子权限记录，支持批量为用户和组织授权

    ## 参数说明
    - **request_data**: 权限数据，格式如下:
      {
        "operator_id": 123,
        "users": [
            {
                "uuid": "user_uuid_1",
                "username": "用户名1"
            }
        ],
        "orgs": [
            {
                "path": "组织1"
            }
        ]
      }

    ## 返回值
    - 创建成功：返回新创建的权限记录列表
    - 创建失败：返回错误信息
    """
    try:
        operator_id = request_data.operator_id
        users = request_data.users or []
        orgs = request_data.orgs or []

        # 检查数据库中已存在的权限记录
        existing_permissions_dict = get_permissions_by_operator(db, operator_id)
        existing_user_uuids = {user['uuid'] for user in existing_permissions_dict['users']}
        existing_org_paths = {org['path'] for org in existing_permissions_dict['orgs']}

        # 从请求中提取用户 UUID 和组织路径
        request_user_uuids = {user.uuid for user in users}
        request_org_paths = {org.path for org in orgs}

        # --- 计算需要新增、删除和跳过的权限 ---

        # 1. 计算需要新增的权限
        new_permissions_data = []
        for user in users:
            if user.uuid not in existing_user_uuids:
                new_permissions_data.append({
                    "operator_id": operator_id,
                    "uuid": user.uuid,
                    "username": user.username,
                    "role_type": 1,
                })
        for org in orgs:
            if org.path not in existing_org_paths:
                new_permissions_data.append({
                    "operator_id": operator_id,
                    "name": org.name,
                    "path": org.path,
                    "role_type": 2,
                })

        # 2. 计算需要删除的权限
        uuids_to_delete = list(existing_user_uuids - request_user_uuids)
        paths_to_delete = list(existing_org_paths - request_org_paths)

        # 3. 计算被跳过的已存在权限
        skipped_users = [user.uuid for user in users if user.uuid in existing_user_uuids]
        skipped_orgs = [org.path for org in orgs if org.path in existing_org_paths]
        skipped_items_count = len(skipped_users) + len(skipped_orgs)

        # 如果没有任何变更，提前返回
        if not new_permissions_data and not uuids_to_delete and not paths_to_delete:
            return response_success(
                data=[],
                msg="权限未发生变化，所有指定用户和组织都已拥有权限"
            )

        # --- 执行数据库操作 ---

        # 批量删除
        if uuids_to_delete:
            delete_permissions_by_user(db, operator_id, uuids_to_delete)
        if paths_to_delete:
            delete_permissions_by_path(db, operator_id, paths_to_delete)

        # 批量创建
        created_permissions = []
        if new_permissions_data:
            created_permissions = create_operator_permission(db, new_permissions_data)

        # --- 构建响应消息 ---
        msg_parts = []
        if created_permissions:
            msg_parts.append(f"成功新增 {len(created_permissions)} 条权限")
        
        deleted_count = len(uuids_to_delete) + len(paths_to_delete)
        if deleted_count > 0:
            msg_parts.append(f"成功删除 {deleted_count} 条权限")

        if skipped_items_count > 0:
            msg_parts.append(f"跳过 {skipped_items_count} 个已存在的用户或组织")
            
        final_msg = "，".join(msg_parts) if msg_parts else "操作成功，无权限变更"

        return response_success(data=created_permissions, msg=final_msg)
    except Exception as e:
        return response_fail(msg=f"算子权限操作失败: {str(e)}")


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
def update_permission_api(permission_id: int, permission_data: dict, db: Session = Depends(get_sync_session)):
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
