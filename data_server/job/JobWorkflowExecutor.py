import json
from data_server.job.JobWorkflow import create_argo_workflow
import os
from loguru import logger

from data_server.database.session import get_sync_session
from data_server.schemas.responses import JOB_STATUS
from data_server.job.JobModels import Job
import uuid
import datetime
from data_server.job.branch_tool import BranchTool

namespace = os.getenv("WORKFLOW_NAMESPACE", "data-flow")

def run_executor(config, job_id, job_name, user_id, user_name, user_token):
    job_type = "tool" if config.job_source == "tool" else "pipeline"    
    uuid_str = str(uuid.uuid4())

    try:
        if config.dataset_path is not None and os.path.exists(config.dataset_path) and not config.repo_id:
            logger.info(
                "User defined valid dataset_path and not defined repo_id, this may cause error during export data to repo")
        else:
            data_path = os.path.join(
                os.getenv("DATA_DIR", "/dataflow_data"), job_name + "_" + uuid_str)
            dataset_path = os.path.join(data_path, 'input')
            export_path = os.path.join(
                data_path,'output','_df_dataset.jsonl')
            config.dataset_path = dataset_path
            config.export_path = export_path

        repo_id = config.repo_id
        work_dir = os.path.dirname(config.export_path)
        config.branch=config.branch if config.branch and len(config.branch) > 0 else 'main'

        branch_tool = BranchTool(repo_id=config.repo_id, user_token=user_token)
        branch_name = branch_tool.get_avai_branch(config.branch)
        if job_type != "tool":
            os.makedirs(work_dir, exist_ok=True)
            with open(os.path.join(work_dir, 'config.yaml'), mode='w') as file:
                file.write(config.yaml())

        json_str = config.model_dump_json()
        json_str = json.dumps(json_str)
        with get_sync_session() as session:
            with session.begin():
                job = session.query(Job).filter(Job.job_id == job_id).first()
                if job:
                    setattr(job, 'uuid', uuid_str)
                    setattr(job, 'data_source', config.dataset_path)
                    setattr(job, 'data_target', config.export_path)
                    setattr(job, 'work_dir', work_dir)
                    setattr(job, 'export_repo_id', repo_id)
                    setattr(job, 'export_branch_name', branch_name)
                    setattr(job, 'status', JOB_STATUS.PROCESSING.value)
                    if job_type == "pipeline":
                        setattr(job, 'first_op', config.process[0].name)

        workflow = create_argo_workflow(namespace=namespace, job_id=job_id, job_conf=json_str, user_id=user_id, user_name=user_name, user_token=user_token, job_type=job_type, uuid_str=uuid_str)
        if workflow:
            logger.info(f"Workflow job_id:{job_id} user_id:{user_id} user_name:{user_name} user_token:{user_token} created successfully")
    except Exception as e:
        logger.error(f"Failed to create workflow job_id:{job_id} error: {e}")
        date_finish = datetime.datetime.now()
        with get_sync_session() as session:
            with session.begin():
                job = session.query(Job).filter(Job.job_id == job_id).first()
                if job:
                    setattr(job, 'status', JOB_STATUS.FAILED.value)
                    setattr(job, 'date_finish', date_finish)
        return


def resource_callback(resource_type: str, event_type: str, resource: dict, job_id: str):
    """process resource status change"""
    try:
        if resource_type == "workflow":
            name = resource['metadata']['name']
            status = resource.get('status', {}).get('phase', 'Unknown')
            logger.info(f"Workflow {name} {event_type}: {status} job_id:{job_id}")

            with get_sync_session() as session:
                with session.begin():
                    job = session.query(Job).filter(Job.job_id == job_id).first()
                    if not job:
                        logger.error(f"Job {job_id} not found")
                        return
                    
                    date_finish = datetime.datetime.now()
                    data_count = 0

                    if status == "Succeeded":
                        try:
                            if job.job_source == "pipeline":
                                trace_dir = os.path.join(job.work_dir, 'trace')
                                first_op = job.first_op
                                count_filename = f"count-{first_op}.txt"
                                count_filepath = os.path.join(trace_dir, count_filename)
                                
                                if os.path.exists(count_filepath):
                                    with open(count_filepath, 'r') as f:
                                        data_lines = f.read().strip()
                                        data_count = int(data_lines)
                            elif job.job_source == "tool":
                                # Count data lines from output file for tool jobs
                                export_path = job.data_target
                                if export_path and os.path.exists(export_path):
                                    try:
                                        # Count lines in output file (usually jsonl format)
                                        with open(export_path, 'r', encoding='utf-8') as f:
                                            data_count = sum(1 for _ in f)
                                    except Exception:
                                        data_count = 0

                            setattr(job, 'data_count', data_count)
                            setattr(job, 'process_count', data_count)
                            setattr(job, 'status', JOB_STATUS.FINISHED.value)
                            
                        except Exception as e:
                            logger.error(f"Error processing successful job: {e}")
                            setattr(job, 'status', JOB_STATUS.FAILED.value)
                            
                    elif status in ["Failed", "Error"]:
                        setattr(job, 'status', JOB_STATUS.FAILED.value)
                        error_message = resource.get('status', {}).get('message', 'Unknown error')
                        logger.error(f"Job {job_id} Workflow {name} {status}: {error_message}")
                    
                    setattr(job, 'date_finish', date_finish)

    except Exception as e:
        logger.error(f"Failed to handle resource callback: {e}")