from data_server.operator.models.operator_permission import OperatorPermission
from data_server.operator.schemas import OperatorPermissionResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


def get_operator_permission(db: Session, permission_id: int) -> Optional[OperatorPermissionResponse]:

    permission = db.query(OperatorPermission).filter(OperatorPermission.id == permission_id).first()
    
    if not permission:
        return None
    
    return OperatorPermissionResponse.model_validate(permission)


def get_operator_permissions(db: Session, skip: int = 0, limit: int = 100) -> List[OperatorPermissionResponse]:

    permissions = db.query(OperatorPermission).offset(skip).limit(limit).all()
    return [OperatorPermissionResponse.model_validate(permission) for permission in permissions]


def get_permissions_by_operator(db: Session, operator_id: int) -> Dict[str, List[Dict[str, Any]]]:

    permissions = db.query(OperatorPermission).filter(OperatorPermission.operator_id == operator_id).all()
    
    response_data = {
        "users": [],
        "orgs": []
    }

    if not permissions:
        return response_data

    for permission in permissions:
        if permission.role_type == 1:
            response_data["users"].append({
                "uuid": permission.uuid,
                "username": permission.username
            })
        elif permission.role_type == 2:
            response_data["orgs"].append({
                "name": permission.name,
                "path": permission.path
            })
            
    return response_data



def get_permissions_by_user(db: Session, uuid: str) -> List[OperatorPermissionResponse]:

    permissions = db.query(OperatorPermission).filter(OperatorPermission.uuid == uuid).all()
    return [OperatorPermissionResponse.model_validate(permission) for permission in permissions]


def get_permissions_by_role_type(db: Session, role_type: int) -> List[OperatorPermissionResponse]:

    permissions = db.query(OperatorPermission).filter(OperatorPermission.role_type == role_type).all()
    return [OperatorPermissionResponse.model_validate(permission) for permission in permissions]


def create_operator_permission(db: Session, permission_data: Union[dict, List[dict]]) -> Union[OperatorPermissionResponse, List[OperatorPermissionResponse]]:


    if isinstance(permission_data, dict):
        permission_list = [permission_data]
        is_single = True
    else:
        permission_list = permission_data
        is_single = False


    db_permissions = []
    for data in permission_list:
        db_permission = OperatorPermission(**data)
        db.add(db_permission)
        db_permissions.append(db_permission)

    db.commit()


    for db_permission in db_permissions:
        db.refresh(db_permission)


    results = [OperatorPermissionResponse.model_validate(db_permission) for db_permission in db_permissions]


    return results[0] if is_single else results


def update_operator_permission(db: Session, permission_id: int, permission_data: dict) -> Optional[OperatorPermissionResponse]:

    db_permission = db.query(OperatorPermission).filter(OperatorPermission.id == permission_id).first()
    if not db_permission:
        return None
    
    for key, value in permission_data.items():
        setattr(db_permission, key, value)
    
    db_permission.updated_at = datetime.now()
    db.commit()
    db.refresh(db_permission)
    
    return OperatorPermissionResponse.model_validate(db_permission)


def delete_operator_permission(db: Session, permission_id: int) -> bool:

    db_permission = db.query(OperatorPermission).filter(OperatorPermission.id == permission_id).first()
    if not db_permission:
        return False
    
    db.delete(db_permission)
    db.commit()
    
    return True


def delete_permissions_by_operator(db: Session, operator_id: int) -> int:

    result = db.query(OperatorPermission).filter(OperatorPermission.operator_id == operator_id).delete()
    db.commit()
    return result


def delete_permissions_by_user(db: Session,operator_id: int, uuid: List[str]) -> int:

    result = db.query(OperatorPermission).filter(
        OperatorPermission.uuid.in_(uuid),
        OperatorPermission.operator_id == operator_id).delete()
    db.commit()
    return result

def delete_permissions_by_path(db: Session,operator_id: int, path: List[str]) -> int:

    result = db.query(OperatorPermission).filter(
        OperatorPermission.path.in_(path),
        OperatorPermission.operator_id == operator_id).delete()
    db.commit()
    return result

def get_permissions_by_path(db: Session, path: List[str]) -> List[OperatorPermissionResponse]:

    result = db.query(OperatorPermission).filter(
        OperatorPermission.path.in_(path)).all()
    return result

