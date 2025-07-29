from data_server.database.bean.base import Base
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Integer
from datetime import datetime
from data_server.utils.id_generator import IdMixin

class OperatorPermission(Base, IdMixin):
    __tablename__ = "operator_permission"

    # id已经由IdMixin提供
    operator_id = Column(BigInteger)
    uuid = Column(String(255))
    username = Column(String(255))  # 用户名
    role_type = Column(Integer)   # 可以是个人或组织

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)