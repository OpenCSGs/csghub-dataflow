from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from data_server.database.bean.base import Base
import datetime


class Job(Base):

    __tablename__ = "job"


    job_id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="Unique task primary key ID, auto-increment integer")
    job_name = Column(String(255), nullable=False, comment="Task name, human-readable task identifier")
    uuid = Column(String(100), comment="Unique task identifier")
    task_run_host = Column(String(100), comment="Server executing the task")

    job_source = Column(String(50), comment="Task source type: 'pipeline' (pipeline task) or 'tool' (tool task)")
    job_type = Column(String(50), comment="Task business type: 'data_refine', 'data_generation', 'data_enhancement', etc.")


    status = Column(String(20), comment="Task execution status: 'Queued', 'Processing', 'Finished', 'Failed', 'Timeout'")


    data_source = Column(String(500), comment="Input data path for the executor to read from")
    data_target = Column(String(500), comment="Output data path for the executor to write results")
    work_dir = Column(String(500), comment="Task work directory for temp files, config, logs, etc.")


    data_count = Column(Integer, comment="Number of data records processed")
    process_count = Column(Integer, comment="Actual processed record count, usually same as data_count")


    date_posted = Column(DateTime, default=datetime.datetime.now, comment="Task creation time, auto-set")
    date_finish = Column(DateTime, comment="Task finish time, set by JobExecutor on completion")


    is_active = Column(Boolean(), default=True, comment="Whether task is active; False means soft-deleted")
    owner_id = Column(Integer, comment="Owner user ID for permission control")
    owner_org_id = Column(String(255), comment="Task owner organization ID")
    owner_org_name = Column(String(255), comment="Task owner organization name")


    repo_id = Column(String(255), comment="Input repo ID, e.g. 'user/dataset-repo', for fetching data from Git")
    branch = Column(String(100), comment="Input branch name, default 'main', branch to fetch data from")
    export_repo_id = Column(String(255), comment="Target repo ID for pushing processed results")
    export_branch_name = Column(String(100), comment="Target branch name for pushing results")


    first_op = Column(String(255), comment="First operator name in pipeline, used for stats file paths")
    yaml_config = Column(Text, comment="Backend YAML task config used at execution time")
    dslText = Column(Text, comment="Frontend YAML task config for UI display and editing")
    flow_id = Column(String(32), comment="DataFlow global task ID submitted to CSGHub")
    cluster_id = Column(String(255), comment="Cluster ID selected when submitting to CSGHub")
    cluster_name = Column(String(255), comment="Cluster name selected when submitting to CSGHub")
    resource_id = Column(Integer, comment="Resource ID selected when submitting to CSGHub")
    resource_name = Column(String(255), comment="Resource name selected when submitting to CSGHub")
    storage_size = Column(String(32), comment="Work volume storage size, e.g. 4Gi")
    csghub_job_id = Column(String(100), comment="Job ID returned by CSGHub")
    csghub_status = Column(String(100), comment="Task status on CSGHub side")
    csghub_request_payload = Column(Text, comment="Request body for CSGHub task creation")
    csghub_response_payload = Column(Text, comment="Raw response from CSGHub")
    namespace_uuid = Column(String(255), comment="namespace UUID in CSGHub DataFlow path")
    namespace_type = Column(String(32), comment="namespace scope: personal / organization")

