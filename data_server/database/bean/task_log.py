from sqlalchemy import Column, Integer, String, Text, BigInteger, UniqueConstraint
from data_server.database.bean.base import Base


class TaskLog(Base):
    """taskLogTable"""
    __tablename__ = "task_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_uid = Column(String(100), nullable=False, index=True)
    task_type = Column(String(20), nullable=False)  # pipeline/datasource/formatify
    level = Column(String(10), nullable=False)
    operator_name = Column(String(100), nullable=True)
    operator_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    create_at = Column(BigInteger, nullable=False)


class OperatorStatus(Base):
    """operatorStateTable"""
    __tablename__ = "operator_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_uid = Column(String(100), nullable=False, index=True)
    operator_name = Column(String(100), nullable=False)
    operator_index = Column(Integer, default=0)
    status = Column(String(20), nullable=False)
    start_time = Column(BigInteger, nullable=True)
    end_time = Column(BigInteger, nullable=True)

    __table_args__ = (UniqueConstraint("job_uid", "operator_name", "operator_index", name="uq_operator_status"),)
