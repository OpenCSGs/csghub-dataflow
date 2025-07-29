from data_server.database.bean.base import Base
from sqlalchemy import Column
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Uuid, func, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from data_server.utils.id_generator import IdMixin

# 算子信息表模型
class OperatorInfo(Base, IdMixin):
    __tablename__ = "operator_info"

    # id已经由IdMixin提供
    operator_name = Column(String(255))
    operator_type = Column(String(255))
    execution_order = Column(Integer)
    is_enabled = Column(Boolean, default=True)
    description = Column(Text)
    before_cleaning = Column(Text)
    after_cleaning = Column(Text)
    icon = Column(Text)  # 图标字段
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# 算子配置表模型
class OperatorConfig(Base, IdMixin):
    __tablename__ = "operator_config"

    # id已经由IdMixin提供
    operator_id = Column(BigInteger)
    config_name = Column(String(255))
    config_type = Column(String(255))
    select_options = Column(JSONB)  # 存储id列表
    default_value = Column(String(255))
    min_value = Column(String(255))
    max_value = Column(String(255))
    slider_step = Column(String(255))
    is_required = Column(Boolean)
    is_spinner = Column(Boolean)
    spinner_step = Column(String(255))
    final_value = Column(Text, comment="用户最终选择的值")  # 改为Text类型
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# operator_config_select_options表模型
class OperatorConfigSelectOptions(Base, IdMixin):
    __tablename__ = "operator_config_select_options"

    # id已经由IdMixin提供
    name = Column(String(255))
    is_enable = Column(Boolean)
    sort = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)