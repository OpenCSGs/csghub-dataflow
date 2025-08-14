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



@router.post("/", summary="创建算子权限")
def create_permission_api(request_data: OperatorPermissionCreateRequest, db: Session = Depends(get_sync_session)):

    try:
        operator_id = request_data.operator_id
        users = request_data.users or []
        orgs = request_data.orgs or []


        existing_permissions_dict = get_permissions_by_operator(db, operator_id)
        existing_user_uuids = {user['uuid'] for user in existing_permissions_dict['users']}
        existing_org_paths = {org['path'] for org in existing_permissions_dict['orgs']}


        request_user_uuids = {user.uuid for user in users}
        request_org_paths = {org.path for org in orgs}




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


        uuids_to_delete = list(existing_user_uuids - request_user_uuids)
        paths_to_delete = list(existing_org_paths - request_org_paths)


        skipped_users = [user.uuid for user in users if user.uuid in existing_user_uuids]
        skipped_orgs = [org.path for org in orgs if org.path in existing_org_paths]
        skipped_items_count = len(skipped_users) + len(skipped_orgs)


        if not new_permissions_data and not uuids_to_delete and not paths_to_delete:
            return response_success(
                data=[],
                msg="权限未发生变化，所有指定用户和组织都已拥有权限"
            )




        if uuids_to_delete:
            delete_permissions_by_user(db, operator_id, uuids_to_delete)
        if paths_to_delete:
            delete_permissions_by_path(db, operator_id, paths_to_delete)


        created_permissions = []
        if new_permissions_data:
            created_permissions = create_operator_permission(db, new_permissions_data)


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



@router.get("/", summary="获取权限列表")
def read_permissions_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_sync_session)):

    try:
        permissions = get_operator_permissions(db, skip, limit)
        return response_success(data=permissions, msg="获取权限列表成功")
    except Exception as e:
        return response_fail(msg=f"获取权限列表失败: {str(e)}")



@router.get("/{permission_id}", summary="根据主键获取单个权限")
def read_permission_api(permission_id: int, db: Session = Depends(get_sync_session)):

    try:
        permission = get_operator_permission(db, permission_id)
        if permission is None:
            return response_fail(msg="权限不存在")
        return response_success(data=permission, msg="获取权限成功")
    except Exception as e:
        return response_fail(msg=f"获取权限失败: {str(e)}")



@router.get("/operator/{operator_id}", summary="根据算子id查询有权限的用户列表")
def read_permissions_by_operator_api(operator_id: int, db: Session = Depends(get_sync_session)):

    try:
        permissions = get_permissions_by_operator(db, operator_id)
        return response_success(data=permissions, msg="获取算子权限成功")
    except Exception as e:
        return response_fail(msg=f"获取算子权限失败: {str(e)}")



@router.get("/user/{uuid}", summary="根据用户id查询有权限的算子列表")
def read_permissions_by_user_api(uuid: str, db: Session = Depends(get_sync_session)):

    try:
        permissions = get_permissions_by_user(db, uuid)
        return response_success(data=permissions, msg="获取用户权限成功")
    except Exception as e:
        return response_fail(msg=f"获取用户权限失败: {str(e)}")



@router.get("/role-type/{role_type}", summary="根据角色类型查询有权限的算子列表")
def read_permissions_by_role_type_api(role_type: int, db: Session = Depends(get_sync_session)):

    try:
        permissions = get_permissions_by_role_type(db, role_type)
        return response_success(data=permissions, msg="获取角色类型权限成功")
    except Exception as e:
        return response_fail(msg=f"获取角色类型权限失败: {str(e)}")



@router.put("/{permission_id}", summary="更新权限")
def update_permission_api(permission_id: int, permission_data: dict, db: Session = Depends(get_sync_session)):

    try:
        permission = update_operator_permission(db, permission_id, permission_data)
        if permission is None:
            return response_fail(msg="权限不存在")
        return response_success(data=permission, msg="更新权限成功")
    except Exception as e:
        return response_fail(msg=f"更新权限失败: {str(e)}")



@router.delete("/{permission_id}", summary="删除权限")
def delete_permission_api(permission_id: int, db: Session = Depends(get_sync_session)):

    try:
        success = delete_operator_permission(db, permission_id)
        if not success:
            return response_fail(msg="权限不存在")
        return response_success(msg="删除权限成功")
    except Exception as e:
        return response_fail(msg=f"删除权限失败: {str(e)}")



@router.delete("/operator/{operator_id}", summary="删除指定算子的所有人权限")
def delete_permissions_by_operator_api(operator_id: int, db: Session = Depends(get_sync_session)):

    try:
        count = delete_permissions_by_operator(db, operator_id)
        return response_success(data={"deleted_count": count}, msg=f"成功删除 {count} 条权限记录")
    except Exception as e:
        return response_fail(msg=f"删除算子权限失败: {str(e)}")



@router.delete("/user/{uuid}", summary="删除指定用户的所有权限")
def delete_permissions_by_user_api(uuid: str, db: Session = Depends(get_sync_session)):

    try:
        count = delete_permissions_by_user(db, uuid)
        return response_success(data={"deleted_count": count}, msg=f"成功删除 {count} 条权限记录")
    except Exception as e:
        return response_fail(msg=f"删除用户权限失败: {str(e)}")
