from data_server.schemas.responses import JOB_STATUS
from data_server.job.JobModels import Job
from data_engine.config import init_configs
from data_engine.core import Executor
from data_engine.core import ToolExecutor
from data_engine.core import RayExecutor
from data_engine.core import ToolExecutorRay
import tempfile
import os
import datetime
import uuid
from data_engine.utils.env import GetDataTopPath
from data_server.database.session import get_sync_session
from data_server.logic.models import ExecutedParams
from data_server.logic.utils import exclude_fields_config
from loguru import logger

RAY_ENABLE = os.environ.get("RAY_ENABLE", False)
# Launch Job
def run_executor(config, job_id, job_name, user_id, user_name, user_token):
    uuid_str = str(uuid.uuid4())
    try:
        if config.dataset_path is not None and os.path.exists(config.dataset_path) and not config.repo_id:
            logger.info(
                "User defined valid dataset_path and not defined repo_id, this may cause error during export data to repo")
        else:
            data_path = os.path.join(
                GetDataTopPath(), job_name + "_" + uuid_str)

            dataset_path = os.path.join(data_path, 'input')
            export_path = os.path.join(data_path, 'output', '_df_dataset.jsonl')
            config.dataset_path = dataset_path
            config.export_path = export_path

        repo_id = config.repo_id
        work_dir = os.path.dirname(config.export_path)
        config.branch=config.branch if config.branch and len(config.branch) > 0 else 'main'
        if config.job_source == "tool":
            # handle tool jobs
            # Validate and provide defaults for required parameters
            if user_id is None:
                logger.warning("user_id is None, using empty string as default")
                user_id = ""
            if user_name is None:
                logger.warning("user_name is None, using empty string as default")
                user_name = ""
            if user_token is None:
                logger.warning("user_token is None, using empty string as default")
                user_token = ""
            
            params = ExecutedParams(
                user_id=user_id,
                user_name=user_name,
                user_token=user_token,
                work_dir=work_dir,
            )
            if RAY_ENABLE == True or RAY_ENABLE == 'True':
                executor = ToolExecutorRay(tool_def=config, params=params)
            else:
                executor = ToolExecutor(tool_def=config, params=params)
        else:
            # handle pipeline jobs:
            yaml_content = config.yaml(exclude=exclude_fields_config)

            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmpfile:
                tmpfile.write(yaml_content)
                temp_dir_str = tmpfile.name
            cfg = init_configs(['--config', temp_dir_str, '--user_id', user_id,
                                '--user_name', user_name, '--user_token', user_token])
            temp_filename = os.path.basename(temp_dir_str)

            work_dir = cfg.work_dir
            temp_work_file = os.path.join(work_dir, temp_filename)
            config_file = os.path.join(work_dir, 'config.yaml')
            try:
                os.remove(temp_dir_str)  # Delete temp file
                os.remove(temp_work_file)
            except FileNotFoundError:
                logger.info(
                    f"The file {temp_work_file} does not exist")
            except PermissionError:
                logger.info(
                    f"Permission denied. You cannot remove {temp_work_file}.")

            with open(config_file, mode='w') as file:
                file.write(config.yaml())

            if RAY_ENABLE == True or RAY_ENABLE == 'True':
                executor = RayExecutor(cfg)
            else:
                executor = Executor(cfg)

        with get_sync_session() as session:
            with session.begin():
                job = session.query(Job).filter(Job.job_id == job_id).first()
                if job:
                    setattr(job, 'uuid', uuid_str)
                    setattr(job, 'data_source', config.dataset_path)
                    setattr(job, 'data_target', config.export_path)
                    setattr(job, 'work_dir', work_dir)
                    setattr(job, 'status', JOB_STATUS.PROCESSING.value)
        _, branch_name = executor.run()
    except Exception as e:
        logger.info(f'executor.run error with: {str(e)}')
        # write data to db after pipeline failed
        date_finish = datetime.datetime.now()
        with get_sync_session() as session:
            with session.begin():
                job = session.query(Job).filter(Job.job_id == job_id).first()
                if job:
                    setattr(job, 'status', JOB_STATUS.FAILED.value)
                    setattr(job, 'date_finish', date_finish)
        return

    # write data to db after pipeline finish
    date_finish = datetime.datetime.now()
    if config.job_source == "tool":
        with get_sync_session() as session:
            with session.begin():
                job = session.query(Job).filter(Job.job_id == job_id).first()
                if job:
                    setattr(job, 'status', JOB_STATUS.FINISHED.value)
                    setattr(job, 'export_repo_id', repo_id)
                    setattr(job, 'export_branch_name', branch_name)
                    setattr(job, 'date_finish', date_finish)
    else:
        trace_dir = os.path.join(work_dir, 'trace')
        first_op = list(cfg.process[0])[0]
        count_filename = f"count-{first_op}.txt"
        count_filepath = os.path.join(trace_dir, count_filename)
        data_count = 0
        if os.path.exists(count_filepath):
            with open(count_filepath, 'r') as f:
                data_lines = f.read().strip()
                data_count = int(data_lines)
        with get_sync_session() as session:
            with session.begin():
                job = session.query(Job).filter(Job.job_id == job_id).first()
                if job:
                    setattr(job, 'data_count', data_count)
                    setattr(job, 'status', JOB_STATUS.FINISHED.value)
                    setattr(job, 'process_count', data_count)
                    setattr(job, 'export_repo_id', repo_id)
                    setattr(job, 'export_branch_name', branch_name)
                    setattr(job, 'date_finish', date_finish)
