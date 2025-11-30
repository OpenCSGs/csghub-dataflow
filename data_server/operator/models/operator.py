from data_server.database.bean.base import Base
from sqlalchemy import Column
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Uuid, func, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class OperatorInfo(Base):
    __tablename__ = "operator_info"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    operator_name = Column(String(255))
    operator_type = Column(String(255))
    execution_order = Column(Integer)
    is_enabled = Column(Boolean, default=True)
    description = Column(Text)
    before_cleaning = Column(Text)
    after_cleaning = Column(Text)
    icon = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_public = Column(Boolean, default=True)
    operator_description = Column(Text)

class OperatorConfig(Base):
    __tablename__ = "operator_config"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    operator_id = Column(BigInteger)
    config_name = Column(String(255))
    config_type = Column(String(255))
    select_options = Column(JSONB)
    default_value = Column(String(255))
    min_value = Column(String(255))
    max_value = Column(String(255))
    slider_step = Column(String(255))
    is_required = Column(Boolean)
    is_spinner = Column(Boolean)
    spinner_step = Column(String(255))
    final_value = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    config_description = Column(Text)

class OperatorConfigSelectOptions(Base):
    __tablename__ = "operator_config_select_options"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255))
    is_enable = Column(Boolean)
    sort = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class OperatorDocument(Base):
    __tablename__ = "operator_document"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    operator_id = Column(BigInteger, ForeignKey("operator_info.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Markdown文档内容
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)