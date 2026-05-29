import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from data_server.database.bean.base import Base


class JobSubTask(Base):
    __tablename__ = "job_subtasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parent_type = Column(String(50), nullable=False, comment="Parent task type: datasource/formatify/pipeline/tool")
    parent_id = Column(Integer, nullable=False, comment="Parent task ID")
    flow_id = Column(String(32), comment="DataFlow global task ID")
    task_id = Column(String(32), nullable=False, comment="Unique subtask ID")
    task_name = Column(String(255), nullable=False, comment="Subtask name")
    task_type = Column(String(100), nullable=False, comment="Subtask type")
    task_sequence = Column(Integer, default=0, comment="Subtask sequence order")
    deps = Column(Text, comment="Dependent task names as JSON list")
    status = Column(String(50), default="Pending", comment="Subtask status")
    request_payload = Column(Text, comment="Subtask submission params as JSON")
    started_at = Column(DateTime, comment="Subtask start time")
    finished_at = Column(DateTime, comment="Subtask finish time")
    error_message = Column(Text, comment="Subtask error message")
    created_at = Column(DateTime, default=datetime.datetime.now, comment="Created at")
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment="Last updated time")

    def to_dict(self):
        return {
            "id": self.id,
            "parent_type": self.parent_type,
            "parent_id": self.parent_id,
            "flow_id": self.flow_id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "task_type": self.task_type,
            "task_sequence": self.task_sequence,
            "deps": self.deps,
            "status": self.status,
            "request_payload": self.request_payload,
            "started_at": self.started_at.strftime("%Y-%m-%d %H:%M:%S") if self.started_at else None,
            "finished_at": self.finished_at.strftime("%Y-%m-%d %H:%M:%S") if self.finished_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
