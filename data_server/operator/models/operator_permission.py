from data_server.database.bean.base import Base
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Integer, Text
from datetime import datetime

class OperatorPermission(Base):
    __tablename__ = "operator_permission"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    operator_id = Column(BigInteger)
    uuid = Column(String(255))
    username = Column(String(255))
    role_type = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    name = Column(String(255))
    path = Column(String(255))
