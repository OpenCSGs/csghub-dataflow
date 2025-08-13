from data_server.database.bean.base import Base
from sqlalchemy import Column, BigInteger, Boolean, DateTime, String, Text, func
from datetime import datetime


class AlgoTemplate(Base):
    """
    算法模板模型
    对应数据库表：algo_templates
    """
    __tablename__ = "algo_templates"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)

    user_id = Column(String(255), comment="用户id")

    name = Column(String(255), comment="算法模块名称")

    description = Column(String(255), comment="算法模版描述")

    type = Column(String(255), comment="算法模版类型")

    buildin = Column(Boolean, comment="是否为内置模版")

    project_name = Column(String(255), comment="项目名称")

    dataset_path = Column(String(255), comment="输入数据集路径")

    exprot_path = Column(String(255), comment="输出数据集路径")

    np = Column(String(255), comment="并行处理的进程数，控制CPU使用和处理速度")

    open_tracer = Column(Boolean, comment="是否开启操作追踪，用于调试和性能分析")

    trace_num = Column(String(255), comment="追踪的样本数量，每个操作追踪多少个样本的处理过程")

    backend_yaml = Column(Text, comment="后端yaml格式")

    dslText = Column(Text, comment="前端yaml格式")

    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="修改时间")

    def __repr__(self):
        return f"<AlgoTemplate(id={self.id}, name='{self.name}', type='{self.type}', user_id='{self.user_id}')>"
