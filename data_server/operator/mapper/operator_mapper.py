from data_server.operator.models.operator import OperatorInfo, OperatorConfig, OperatorConfigSelectOptions
from data_server.operator.models.operator_permission import OperatorPermission
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from data_server.operator.schemas import OperatorResponse, OperatorConfigResponse, OperatorConfigSelectOptionsResponse


def get_operator(db: Session, operator_id: int) -> Optional[OperatorResponse]:
    """获取单个算子信息及其配置"""
    # 从数据库中查询指定ID的算子
    operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
    
    # 如果找不到算子，返回None
    if not operator:
        return None
    
    # 查询该算子关联的所有配置
    configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator_id).all()
    
    # 创建配置响应对象列表
    config_responses = [OperatorConfigResponse.model_validate(config) for config in configs] # type: List[OperatorConfigResponse]
    
    # 创建算子响应对象并添加配置
    response = OperatorResponse.model_validate(operator)
    response.configs = config_responses
    
    return response


def get_operators(db: Session, skip: int = 0, limit: int = 100) -> List[OperatorResponse]:
    """获取多个算子信息及其配置"""
    operators = db.query(OperatorInfo).offset(skip).limit(limit).all()
    result = []
    
    for operator in operators:
        # 查询该算子关联的所有配置
        configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator.id).all()
        
        # 创建配置响应对象列表
        config_responses = [OperatorConfigResponse.model_validate(config) for config in configs]
        
        # 创建算子响应对象并添加配置
        response = OperatorResponse.model_validate(operator)
        response.configs = config_responses
        result.append(response)
    
    return result


def create_operator(db: Session, operator_data: dict) -> OperatorResponse:
    """创建算子及其配置"""
    # 提取configs数据
    configs_data = operator_data.pop("configs", [])
    
    # 创建算子
    db_operator = OperatorInfo(**operator_data)
    db.add(db_operator)
    db.flush()  # 刷新以获取ID但不提交事务
    
    # 创建配置
    db_configs = []
    for config_data in configs_data:
        config_data["operator_id"] = db_operator.id
        db_config = OperatorConfig(**config_data)
        db.add(db_config)
        db_configs.append(db_config)
    
    # 提交事务
    db.commit()
    db.refresh(db_operator)
    
    # 创建配置响应对象列表
    config_responses = []
    for config in db_configs:
        db.refresh(config)
        config_responses.append(OperatorConfigResponse.model_validate(config))
    
    # 创建并返回响应对象
    response = OperatorResponse.model_validate(db_operator)
    response.configs = config_responses
    
    return response


def update_operator(db: Session, operator_id: int, operator_data: dict) -> Optional[OperatorResponse]:
    """更新算子及其配置"""
    # 检查算子是否存在
    db_operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
    if not db_operator:
        return None
    
    # 提取configs数据
    configs_data = operator_data.pop("configs", None)
    
    # 更新算子数据
    for key, value in operator_data.items():
        setattr(db_operator, key, value)
    
    db_operator.updated_at = datetime.now()
    
    # 如果提供了配置数据，则更新配置
    db_configs = []
    if configs_data is not None:
        for config_data in configs_data:
            # 检查是否提供了id
            config_id = config_data.get("id")
            if config_id:
                # 如果提供了id，查询配置是否存在且属于该算子
                existing_config = db.query(OperatorConfig).filter(
                    OperatorConfig.id == config_id,
                    OperatorConfig.operator_id == operator_id
                ).first()
                
                if not existing_config:
                    # 如果配置不存在或不属于该算子，报错
                    raise ValueError(f"算子配置ID {config_id} 不存在")

                # 更新配置
                for key, value in config_data.items():
                    if key != "id" and key != "operator_id":  # 不更新id和operator_id
                        # 对于select_options字段，确保值不为None才进行更新
                        if key == "select_options" and value is None:
                            continue
                        # 添加调试日志
                        print(f"更新字段 {key}: {value} (类型: {type(value)})")
                        old_value = getattr(existing_config, key, None)
                        print(f"原值: {old_value}")
                        setattr(existing_config, key, value)
                        new_value = getattr(existing_config, key, None)
                        print(f"新值: {new_value}")
                
                # 确保添加到会话中
                db.add(existing_config)
                db_configs.append(existing_config)
            else:
                # 如果没有提供id，创建新配置
                new_config_data = config_data.copy()
                new_config_data["operator_id"] = operator_id
                # 雪花ID会在模型中自动生成（如果模型配置了自动生成机制）
                db_config = OperatorConfig(**new_config_data)
                db.add(db_config)
                db_configs.append(db_config)
    
    db.commit()
    db.refresh(db_operator)
    
    # 获取更新后的配置
    configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator_id).all()
    config_responses = [OperatorConfigResponse.model_validate(config) for config in configs]
    
    # 创建并返回响应对象
    response = OperatorResponse.model_validate(db_operator)
    response.configs = config_responses
    
    return response


def delete_operator(db: Session, operator_id: int) -> bool:
    """删除算子及其配置"""
    # 检查算子是否存在
    db_operator = db.query(OperatorInfo).filter(OperatorInfo.id == operator_id).first()
    if not db_operator:
        return False
    
    # 删除相关配置
    db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator_id).delete()
    
    # 删除算子
    db.delete(db_operator)
    db.commit()
    
    return True

# 获取所有operator_config_select_options选项

def get_operator_config_select_options_list(db: Session, only_enable: bool = True):
    query = db.query(OperatorConfigSelectOptions)
    if only_enable:
        query = query.filter(OperatorConfigSelectOptions.is_enable == True)
    options = query.order_by(OperatorConfigSelectOptions.sort).all()
    return [OperatorConfigSelectOptionsResponse.model_validate(opt) for opt in options]

# 根据id获取operator_config_select_options单条记录

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


def get_operators_grouped_by_type(db: Session,uuid: str) -> List[Dict[str, Any]]:
    """获取所有算子并按类型分组"""
    # 获取所有算子
    operators = db.query(OperatorInfo).filter(OperatorInfo.is_enabled == True).all()

    # # 获取用户有权限访问的算子ID列表
    # permitted_operator_ids = db.query(OperatorPermission.operator_id).filter(
    #     OperatorPermission.uuid == uuid
    # ).all()
    #
    # # 将查询结果转换为ID列表
    # permitted_operator_ids = [op[0] for op in permitted_operator_ids]
    #
    # # 获取所有用户有权限访问且启用的算子
    # operators = db.query(OperatorInfo).filter(
    #     OperatorInfo.is_enabled == True,
    #     OperatorInfo.id.in_(permitted_operator_ids)
    # ).all()

    # 定义算子类型列表
    operator_types = ["Mapper", "Filter", "Deduplicator", "Selector", "Formatter"]

    # 初始化结果字典
    grouped_operators = {}
    for op_type in operator_types:
        grouped_operators[op_type] = []

    # 按类型分组算子
    for operator in operators:
        # 查询该算子关联的所有配置
        configs = db.query(OperatorConfig).filter(OperatorConfig.operator_id == operator.id).all()

        # 创建配置响应对象列表，并处理select_options和default_value格式
        config_responses = []
        for config in configs:
            # 手动构建配置响应对象，排除created_at和updated_at字段
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

            # 如果存在select_options，将ID列表转换为{value, label}格式
            if config_dict["select_options"]:
                formatted_options = []
                for option_id in config_dict["select_options"]:
                    # 调用现有函数获取选项详情
                    option_detail = get_operator_config_select_option_by_id(db, option_id)
                    if option_detail:
                        formatted_options.append({
                            "value": str(option_id),
                            "label": option_detail.name
                        })
                config_dict["select_options"] = formatted_options

            # 过滤掉值为空的字段（None、空字符串、空列表等），但final_value字段无论是否为空都要返回
            filtered_config_dict = {}
            for key, value in config_dict.items():
                if key == "final_value" or (value is not None and value != "" and value != [] and value != {}):
                    filtered_config_dict[key] = value

            config_responses.append(filtered_config_dict)

        # 手动构建算子响应对象，排除指定字段
        operator_dict = {
            "id": operator.id,
            "operator_name": operator.operator_name,
            "operator_type": operator.operator_type,
            "icon": operator.icon,
            "configs": config_responses
        }

        # 根据operator_type分组
        if operator.operator_type in grouped_operators:
            grouped_operators[operator.operator_type].append(operator_dict)
        else:
            # 如果是未知类型，添加到其他分类或忽略
            pass

    # 转换为所需的格式
    result = []
    for type_name, operators_list in grouped_operators.items():
        result.append({
            "typeName": type_name,
            "list": operators_list
        })

    return result
