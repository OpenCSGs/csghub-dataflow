from data_server.database.bean.base import Base
from sqlalchemy import Column, BigInteger, Boolean, DateTime, String, Text, func
from datetime import datetime


class AlgoTemplate(Base):

    __tablename__ = "algo_templates"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)

    user_id = Column(String(255), comment="User ID")

    name = Column(String(255), comment="Algorithm module name")

    description = Column(String(255), comment="Algorithm template description")

    type = Column(String(255), comment="Algorithm template type")

    buildin = Column(Boolean, comment="Whether built-in template")

    project_name = Column(String(255), comment="Project name")

    dataset_path = Column(String(255), comment="Input dataset path")

    exprot_path = Column(String(255), comment="Output dataset path")

    np = Column(String(255), comment="Number of parallel processes; controls CPU usage and speed")

    open_tracer = Column(Boolean, comment="Whether to enable operation tracing for debugging and profiling")

    trace_num = Column(String(255), comment="Number of samples to trace per operation")

    backend_yaml = Column(Text, comment="Backend YAML format")

    dslText = Column(Text, comment="Frontend YAML format")

    created_at = Column(DateTime, default=datetime.now, comment="Created at")

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="Updated at")

    def __repr__(self):
        return f"<AlgoTemplate(id={self.id}, name='{self.name}', type='{self.type}', user_id='{self.user_id}')>"
