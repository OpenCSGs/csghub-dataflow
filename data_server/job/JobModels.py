from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from data_server.database.bean.base import Base
import datetime


class Job(Base):

    __tablename__ = "job"


    job_id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="任务唯一主键ID，自增整数")
    job_name = Column(String(255), nullable=False, comment="任务名称，用户可读的任务标识")
    uuid = Column(String(100), comment="任务唯一标识")
    job_celery_uuid = Column(String(100), comment="celery任务调度唯一标识")
    task_run_host = Column(String(100), comment="任务执行的服务器")
    job_celery_work_name = Column(String(255), comment="任务执行的服务器名称")

    job_source = Column(String(50), comment="任务来源类型：'pipeline'(流水线任务) 或 'tool'(工具任务)")
    job_type = Column(String(50), comment="任务业务类型：'data_refine'(数据精炼)、'data_generation'(数据生成)、'data_enhancement'(数据增强)等")


    status = Column(String(20), comment="任务执行状态：'Queued'(排队)、'Processing'(处理中)、'Finished'(完成)、'Failed'(失败)、'Timeout'(超时)")


    data_source = Column(String(500), comment="输入数据路径，告诉执行器从哪里读取数据")
    data_target = Column(String(500), comment="输出数据路径，告诉执行器将结果保存到哪里")
    work_dir = Column(String(500), comment="任务工作目录，存放临时文件、配置文件、日志等")


    data_count = Column(Integer, comment="处理的数据条数")
    process_count = Column(Integer, comment="实际处理的数据条数，通常与data_count相同")


    date_posted = Column(DateTime, default=datetime.datetime.now, comment="任务创建时间，自动设置")
    date_finish = Column(DateTime, comment="任务完成时间，由JobExecutor在任务完成时设置")


    is_active = Column(Boolean(), default=True, comment="任务是否激活/有效，False表示已删除(软删除标记)")
    owner_id = Column(Integer, comment="任务所有者的用户ID，用于权限控制")


    repo_id = Column(String(255), comment="输入数据的仓库ID，如'user/dataset-repo'，用于从Git仓库获取数据")
    branch = Column(String(100), comment="输入数据的分支名，默认'main'，指定从哪个分支获取数据")
    export_repo_id = Column(String(255), comment="输出数据的目标仓库ID，将处理结果推送到指定仓库")
    export_branch_name = Column(String(100), comment="输出数据的目标分支名，将结果推送到指定分支")


    first_op = Column(String(255), comment="流水线中第一个操作符的名称，用于统计文件路径生成")
    yaml_config = Column(Text, comment="后端yaml格式任务配置数据，后端执行时使用的完整配置")
    dslText = Column(Text, comment="前端yaml格式任务配置数据，前端界面展示和编辑使用")

