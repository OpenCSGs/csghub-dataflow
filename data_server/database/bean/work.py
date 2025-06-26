from data_server.database.bean.base import Base
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Uuid, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Column

class Worker(Base):
    __tablename__ = "workers"

    worker_uuid = Column(String(128), primary_key=True)
    user_id = Column(Integer,nullable=True)
    worker_name = Column(String(256), nullable=True)
