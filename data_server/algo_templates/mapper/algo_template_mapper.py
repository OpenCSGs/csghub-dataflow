from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
import yaml

from data_server.algo_templates.model import AlgoTemplate
from data_server.algo_templates.utils.parse_algo_dslText import convert_raw_to_processed


def find_repeat_name(db: Session, name: str, user_id: str):
    return db.query(AlgoTemplate).filter(
        AlgoTemplate.name == name,
        AlgoTemplate.user_id == user_id
    ).first()

def get_all_templates(db: Session, user_id: str) -> List[AlgoTemplate]:
    """
    查询所有算法模板记录
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        List[AlgoTemplate]: 算法模板列表
    """
    return db.query(AlgoTemplate).filter(AlgoTemplate.user_id == user_id).all()

def get_template_by_id(db: Session, template_id: int, user_id: str) -> Optional[AlgoTemplate]:
    """
    根据模板ID查询单个算法模板
    
    Args:
        db: 数据库会话
        template_id: 模板ID
        user_id: 用户ID
        
    Returns:
        Optional[AlgoTemplate]: 算法模板对象或None
    """
    # 先根据模板ID查询
    template = db.query(AlgoTemplate).filter(AlgoTemplate.id == template_id).first()
    
    if not template:
        return None
    
    # 如果是内置模板，直接返回
    if template.buildin:
        return template
    
    # 如果不是内置模板，需要验证用户权限
    if template.user_id == user_id:
        return template
    
    return None


def create_template(db: Session, template_data: dict) -> AlgoTemplate:
    """
    创建新的算法模板
    
    Args:
        db: 数据库会话
        template_data: 模板数据字典
        
    Returns:
        AlgoTemplate: 创建的算法模板对象
    """
    template = AlgoTemplate(**template_data)
    fields_to_insert = {
        "buildin":template.buildin,
        "project_name":template.project_name,
        "dataset_path":template.dataset_path,
        "exprot_path":template.exprot_path,
        "np":template.np,
        "open_tracer":template.open_tracer,
        "trace_num":template.trace_num,
    }
    # 解析YAML为字典
    dsl_data = yaml.safe_load(template.dslText)
    dsl_data.update(fields_to_insert)
    # 将字典重新生成YAML字符串
    new_dsl_data = yaml.dump(dsl_data, sort_keys=False, default_flow_style=False, indent=2, width=float("inf"))
    # 将前端yaml字符串转换为后端所需的yaml字符串
    new_backend_yaml = convert_raw_to_processed(new_dsl_data)
    template.backend_yaml = new_backend_yaml
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template_by_id(db: Session, template_id: int, user_id: str, template_data: dict) -> Optional[AlgoTemplate]:
    """
    根据模板ID和用户ID更新算法模板
    
    Args:
        db: 数据库会话
        template_id: 模板ID
        user_id: 用户ID，用于权限验证
        template_data: 更新的模板数据
        
    Returns:
        Optional[AlgoTemplate]: 更新成功返回模板对象，模板不存在返回None
    """
    template = db.query(AlgoTemplate).filter(
        AlgoTemplate.id == template_id,
        AlgoTemplate.user_id == user_id
    ).first()
    
    if not template:
        return None
    
    # 更新模板字段（只更新提供的字段，支持空字符串）
    for key, value in template_data.items():
        if hasattr(template, key):
            setattr(template, key, value)

    # 如果本次更新包含 dslText 字段，则重新生成 backend_yaml
    if 'dslText' in template_data:
        import yaml
        from data_server.algo_templates.utils.parse_algo_dslText import convert_raw_to_processed
        fields_to_insert = {
            "buildin": template.buildin,
            "project_name": template.project_name,
            "dataset_path": template.dataset_path,
            "exprot_path": template.exprot_path,
            "np": template.np,
            "open_tracer": template.open_tracer,
            "trace_num": template.trace_num,
        }
        dsl_data = yaml.safe_load(template.dslText)
        dsl_data.update(fields_to_insert)
        new_dsl_data = yaml.dump(dsl_data, sort_keys=False, default_flow_style=False, indent=2, width=float("inf"))
        new_backend_yaml = convert_raw_to_processed(new_dsl_data)
        template.backend_yaml = new_backend_yaml

    db.commit()
    db.refresh(template)
    return template


def delete_template_by_id(db: Session, template_id: int, user_id: str) -> bool:
    """
    根据模板ID和用户ID删除算法模板
    
    Args:
        db: 数据库会话
        template_id: 模板ID
        user_id: 用户ID，用于权限验证
        
    Returns:
        bool: 删除成功返回True，模板不存在返回False
    """
    template = db.query(AlgoTemplate).filter(
        AlgoTemplate.id == template_id,
        AlgoTemplate.user_id == user_id
    ).first()
    
    if not template:
        return False
    
    db.delete(template)
    db.commit()
    return True


def get_templates_by_query(db: Session, user_id: str,
                           page: int = 1, page_size: int = 10, 
                           buildin: Optional[bool] = None) -> Tuple[List[AlgoTemplate], int]:
    """
    根据查询条件分页查询算法模板
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        page: 页码
        page_size: 每页数量
        buildin: 是否为内置模版过滤。如果为True，则查询所有内置模板，忽略user_id。
        
    Returns:
        Tuple[List[AlgoTemplate], int]: (模板列表, 总数量)
    """
    query = db.query(AlgoTemplate)

    if buildin is True:
        # 如果 buildin 为 True, 查询所有 buildin 为 True 的模板, 忽略 user_id
        query = query.filter(AlgoTemplate.buildin == True)
    elif buildin is False:
        # 如果 buildin 为 False, 只查询当前用户的非内置模板
        query = query.filter(AlgoTemplate.user_id == user_id, AlgoTemplate.buildin == False)
    else:
        # 如果 buildin 为 None, 查询所有内置模板 + 当前用户的非内置模板
        from sqlalchemy import or_, and_
        query = query.filter(
            or_(
                AlgoTemplate.buildin == True,
                and_(AlgoTemplate.buildin == False, AlgoTemplate.user_id == user_id)
            )
        )
    
    # 获取总数量
    total = query.count()
    
    # 分页查询
    templates = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return templates, total
