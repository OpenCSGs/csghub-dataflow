from data_server.operator.mapper.operator_permission_mapper import get_permissions_by_path
from data_server.operator.models.operator import OperatorInfo, OperatorConfig, OperatorConfigSelectOptions
from data_server.operator.models.operator_permission import OperatorPermission
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from data_server.operator.schemas import OperatorResponse, OperatorConfigResponse, OperatorConfigSelectOptionsResponse
from loguru import logger


def get_operator(db: Session, operator_id: int) -> Optional[OperatorResponse]:


    operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
    

    if not operator:
        return None
    

    configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator_id).all()
    

    config_responses = [OperatorConfigResponse.model_validate(config) for config in configs] # type: List[OperatorConfigResponse]
    

    response = OperatorResponse.model_validate(operator)
    response.configs = config_responses
    
    return response


def get_operators(db: Session, skip: int = 0, limit: int = 100) -> List[OperatorResponse]:

    operators = db.query(OperatorInfo).offset(skip).limit(limit).all()
    result = []
    
    for operator in operators:

        configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator.id).all()
        

        config_responses = [OperatorConfigResponse.model_validate(config) for config in configs]
        

        response = OperatorResponse.model_validate(operator)
        response.configs = config_responses
        result.append(response)
    
    return result


def create_operator(db: Session, operator_data: dict) -> OperatorResponse:


    configs_data = operator_data.pop("configs", [])
    

    db_operator = OperatorInfo(**operator_data)
    db.add(db_operator)
    db.flush()
    

    db_configs = []
    for config_data in configs_data:
        config_data["operator_id"] = db_operator.id
        db_config = OperatorConfig(**config_data)
        db.add(db_config)
        db_configs.append(db_config)
    

    db.commit()
    db.refresh(db_operator)
    

    config_responses = []
    for config in db_configs:
        db.refresh(config)
        config_responses.append(OperatorConfigResponse.model_validate(config))
    

    response = OperatorResponse.model_validate(db_operator)
    response.configs = config_responses
    
    return response


def update_operator(db: Session, operator_id: int, operator_data: dict) -> Optional[OperatorResponse]:


    db_operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
    if not db_operator:
        return None
    

    configs_data = operator_data.pop("configs", None)


    for key, value in operator_data.items():
        setattr(db_operator, key, value)
    
    db_operator.updated_at = datetime.now()

    db_configs = []
    if configs_data is not None:
        for config_data in configs_data:
            config_id = config_data.get("id")
            if config_id:
                existing_config = db.query(OperatorConfig).filter(
                    OperatorConfig.id == config_id,
                    OperatorConfig.operator_id == operator_id
                ).first()
                
                if not existing_config:
                    raise ValueError(f"算子配置ID {config_id} 不存在")

                for key, value in config_data.items():
                    if key != "id" and key != "operator_id":
                        if key == "select_options" and value is None:
                            continue
                        print(f"更新字段 {key}: {value} (类型: {type(value)})")
                        old_value = getattr(existing_config, key, None)
                        print(f"原值: {old_value}")
                        setattr(existing_config, key, value)
                        new_value = getattr(existing_config, key, None)
                        print(f"新值: {new_value}")

                db.add(existing_config)
                db_configs.append(existing_config)
            else:
                new_config_data = config_data.copy()
                new_config_data["operator_id"] = operator_id
                db_config = OperatorConfig(**new_config_data)
                db.add(db_config)
                db_configs.append(db_config)
    
    db.commit()
    db.refresh(db_operator)

    configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator_id).all()
    config_responses = [OperatorConfigResponse.model_validate(config) for config in configs]

    response = OperatorResponse.model_validate(db_operator)
    response.configs = config_responses
    
    return response


def delete_operator(db: Session, operator_id: int) -> bool:


    db_operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
    if not db_operator:
        return False
    

    db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator_id).delete()
    

    db.delete(db_operator)
    db.commit()
    
    return True



def get_operator_config_select_options_list(db: Session, only_enable: bool = True):
    query = db.query(OperatorConfigSelectOptions)
    if only_enable:
        query = query.filter(OperatorConfigSelectOptions.is_enable == True)
    options = query.order_by(OperatorConfigSelectOptions.sort).all()
    return [OperatorConfigSelectOptionsResponse.model_validate(opt) for opt in options]



def get_operator_config_select_option_by_id(db: Session, option_id: int):
    option = db.query(OperatorConfigSelectOptions).filter(OperatorConfigSelectOptions.id == option_id).first()
    if not option:
        return None
    return OperatorConfigSelectOptionsResponse.model_validate(option)

def create_operator_config_select_option(db: Session, option_data):
    option = OperatorConfigSelectOptions(**option_data)
    db.add(option)
    db.commit()
    db.refresh(option)
    return OperatorConfigSelectOptionsResponse.model_validate(option)


def get_operators_grouped_by_type(db: Session) -> List[Dict[str, Any]]:


    operators = db.query(OperatorInfo).all()


    operator_types = ["Mapper", "Filter", "Deduplicator", "Selector", "Formatter"]


    grouped_operators = {}
    for op_type in operator_types:
        grouped_operators[op_type] = []


    for operator in operators:

        configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator.id).all()


        config_responses = []
        for config in configs:

            config_dict = {
                "id": config.id,
                "operator_id": config.operator_id,
                "config_name": config.config_name,
                "config_type": config.config_type,
                "select_options": config.select_options,
                "default_value": config.default_value,
                "min_value": config.min_value,
                "max_value": config.max_value,
                "slider_step": config.slider_step,
                "is_required": config.is_required,
                "is_spinner": config.is_spinner,
                "spinner_step": config.spinner_step,
                "final_value": config.final_value
            }


            if config_dict["select_options"]:
                formatted_options = []
                for option_id in config_dict["select_options"]:

                    option_detail = get_operator_config_select_option_by_id(db, option_id)
                    if option_detail:
                        formatted_options.append({
                            "value": str(option_id),
                            "label": option_detail.name
                        })
                config_dict["select_options"] = formatted_options


            filtered_config_dict = {}
            for key, value in config_dict.items():
                if key == "final_value" or (value is not None and value != "" and value != [] and value != {}):
                    filtered_config_dict[key] = value

            config_responses.append(filtered_config_dict)


        operator_dict = {
            "id": operator.id,
            "operator_name": operator.operator_name,
            "operator_type": operator.operator_type,
            "icon": operator.icon,
            "configs": config_responses
        }


        if operator.operator_type in grouped_operators:
            grouped_operators[operator.operator_type].append(operator_dict)
        else:

            pass


    result = []
    for type_name, operators_list in grouped_operators.items():
        result.append({
            "typeName": type_name,
            "list": operators_list
        })

    return result

def get_operators_grouped_by_condition(db: Session, uuid: str, paths: List[str]) -> List[Dict[str, Any]]:

    personal_operator_ids = {
        op_id for op_id, in db.query(OperatorPermission.operator_id).filter(OperatorPermission.uuid == uuid)
    }


    org_operator_ids = set()
    if paths:

        permission_list = get_permissions_by_path(db, paths)
        org_operator_ids = {permission.operator_id for permission in permission_list}


    all_permitted_ids = personal_operator_ids.union(org_operator_ids)


    if not all_permitted_ids:
        # if_there_is_no_permission_display_all_operators
        operators = db.query(OperatorInfo).order_by(OperatorInfo.id).all()
    else:
        operators = db.query(OperatorInfo).filter(
            OperatorInfo.id.in_(list(all_permitted_ids))
        ).order_by(OperatorInfo.id).all()


    operator_types = ["Mapper", "Filter", "Deduplicator", "Selector", "Formatter"]


    grouped_operators = {}
    for op_type in operator_types:
        grouped_operators[op_type] = []


    for operator in operators:

        configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator.id).order_by(OperatorConfig.id).all()


        config_responses = []
        for config in configs:

            config_dict = {
                "id": config.id,
                "operator_id": config.operator_id,
                "config_name": config.config_name,
                "config_type": config.config_type,
                "select_options": config.select_options,
                "default_value": config.default_value,
                "min_value": config.min_value,
                "max_value": config.max_value,
                "slider_step": config.slider_step,
                "is_required": config.is_required,
                "is_spinner": config.is_spinner,
                "spinner_step": config.spinner_step,
                "final_value": config.final_value
            }


            if config_dict["select_options"]:
                formatted_options = []
                for option_id in config_dict["select_options"]:

                    option_detail = get_operator_config_select_option_by_id(db, option_id)
                    if option_detail:
                        formatted_options.append({
                            "value": str(option_id),
                            "label": option_detail.name
                        })
                config_dict["select_options"] = formatted_options


            filtered_config_dict = {}
            for key, value in config_dict.items():
                if key == "final_value" or (value is not None and value != "" and value != [] and value != {}):
                    filtered_config_dict[key] = value

            config_responses.append(filtered_config_dict)


        operator_dict = {
            "id": operator.id,
            "operator_name": operator.operator_name,
            "operator_type": operator.operator_type,
            "icon": operator.icon,
            "configs": config_responses
        }


        if operator.operator_type in grouped_operators:
            grouped_operators[operator.operator_type].append(operator_dict)
        else:

            pass


    result = []
    for type_name, operators_list in grouped_operators.items():
        result.append({
            "typeName": type_name,
            "list": operators_list
        })

    return result
