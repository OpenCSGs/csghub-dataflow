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

    return db.query(AlgoTemplate).filter(AlgoTemplate.user_id == user_id).all()

def get_template_by_id(db: Session, template_id: int, user_id: str) -> Optional[AlgoTemplate]:


    template = db.query(AlgoTemplate).filter(AlgoTemplate.id == template_id).first()
    
    if not template:
        return None
    

    if template.buildin:
        return template
    

    if template.user_id == user_id:
        return template
    
    return None


def create_template(db: Session, template_data: dict) -> AlgoTemplate:

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

    dsl_data = yaml.safe_load(template.dslText)
    dsl_data.update(fields_to_insert)

    new_dsl_data = yaml.dump(dsl_data, sort_keys=False, default_flow_style=False, indent=2, width=float("inf"))

    new_backend_yaml = convert_raw_to_processed(new_dsl_data)
    template.backend_yaml = new_backend_yaml
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template_by_id(db: Session, template_id: int, user_id: str, template_data: dict) -> Optional[AlgoTemplate]:

    template = db.query(AlgoTemplate).filter(
        AlgoTemplate.id == template_id,
        AlgoTemplate.user_id == user_id
    ).first()
    
    if not template:
        return None
    

    for key, value in template_data.items():
        if hasattr(template, key):
            setattr(template, key, value)


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

    template = db.query(AlgoTemplate).filter(
        AlgoTemplate.id == template_id,
        AlgoTemplate.user_id == user_id,
        AlgoTemplate.buildin == False
    ).first()
    
    if not template:
        return False
    
    db.delete(template)
    db.commit()
    return True


def get_templates_by_query(db: Session, user_id: str,
                           page: int = 1, page_size: int = 10, 
                           buildin: Optional[bool] = None) -> Tuple[List[AlgoTemplate], int]:

    query = db.query(AlgoTemplate)

    if buildin is True:

        query = query.filter(AlgoTemplate.buildin == True)
    elif buildin is False:

        query = query.filter(AlgoTemplate.user_id == user_id, AlgoTemplate.buildin == False)
    else:

        from sqlalchemy import or_, and_
        query = query.filter(
            or_(
                AlgoTemplate.buildin == True,
                and_(AlgoTemplate.buildin == False, AlgoTemplate.user_id == user_id)
            )
        )
    

    total = query.count()
    

    templates = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return templates, total
