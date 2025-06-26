from data_server.job.JobModels import Job
from data_server.schemas import responses
from sqlalchemy.orm import Session
from datetime import datetime
from data_server.logic.models import Recipe
from data_server.logic.utils import read_jsonl_to_list, data_format, setup_executor
import os
import shutil
import re
from data_server.database.session import get_sync_session
from multiprocessing import Process


def delete_directory_if_exists(directory_path):
    if not directory_path:
        print("Directory path is not provided.")
        return
    if os.path.exists(directory_path) and os.path.isdir(directory_path):
        try:
            shutil.rmtree(directory_path)
            print(
                f"Directory {directory_path} and all its contents have been deleted.")
        except Exception as e:
            print(
                f"An error occurred while trying to delete {directory_path}: {e}")
    else:
        print(
            f"Directory {directory_path} does not exist or is not a directory.")


def list_jobs(user_id, session: Session, isadmin=False):
    # jobs = session.query(Job).all()
    # if user is supper user, then should get all users' jobs
    if isadmin:
        jobs = session.query(Job).order_by(Job.job_id.desc()).all()
    else:
        jobs = session.query(Job).filter(
            Job.owner_id == user_id).order_by(Job.job_id.desc()).all()

    if jobs is None:
        jobs = []  # ensure not return None

    return jobs


def get_job_data(job_id: int, user_id, session: Session, isadmin=False):
    item = None
    if isadmin:
        item = session.query(Job).filter(Job.job_id == job_id).first()
    else:
        item = session.query(Job).filter(
            Job.owner_id == user_id).filter(Job.job_id == job_id).first()
    return item


def retreive_job(job_id: int, user_id, session: Session, isadmin=False):
    updated_job_details = {'job': {}, 'config_content': {}}
    item = None
    if isadmin:
        item = session.query(Job).filter(Job.job_id == job_id).first()
    else:
        item = session.query(Job).filter(Job.owner_id == user_id,
                                         Job.job_id == job_id).first()

    if item is None:
        return item

    job_details: responses.JobDetails = item
    try:
        work_dir = job_details.work_dir
        

        config_file = os.path.join(work_dir, 'config.yaml')
        # read config.yaml
        with open(config_file, 'r') as f:
            config_content = Recipe.parse_yaml(f.read())
        trace_dir = os.path.join(work_dir, 'trace')

        # init process
        process = config_content.process
        # set op.status to responses.JOB_STATUS.FAILED.value, if the Job status is responses.JOB_STATUS.FAILED.value
        if job_details.status == responses.JOB_STATUS.FAILED.value:
            for op in process:
                op.status = responses.JOB_STATUS.FAILED.value

        for filename in os.listdir(trace_dir):
            name_without_ext = filename.split('.')[0].split('-')[1]

            if filename.endswith('.jsonl'):
                jsonl_filepath = os.path.join(trace_dir, filename)
                data_list = read_jsonl_to_list(jsonl_filepath)
                for op in process:
                    if op.name == name_without_ext:
                        if not op.type:
                            op.type = 'Others'
                        op.data = data_format(data_list, op.type)
            count_filename = f"count-{name_without_ext}.txt"
            if filename == count_filename:
                count_filepath = os.path.join(trace_dir, count_filename)
                if os.path.exists(count_filepath):
                    with open(count_filepath, 'r') as f:
                        data_lines = f.read().strip()
                        for op in process:
                            if op.name == name_without_ext:
                                op.status = responses.JOB_STATUS.FINISHED.value
                                op.data_lines = int(data_lines)
        # handle blank datas
        for op in process:
            if not op.data:
                if not op.type:
                    op.type = 'Others'
                op.data = data_format(op.data, op.type)
        config_dict = config_content.model_dump()
        config_dict['process'] = process
        updated_job_details = {
            'job': job_details,
            'config_content': config_dict
        }
    except Exception as e:
        print(f"Warn: retreive job config_content failed, maybe it's caused by the job_source is tool: {str(e)}")
        updated_job_details = {
            'job': job_details,
            'config_content': {}
        }
    return updated_job_details


def retreive_log(job_id: int, user_id, session: Session, isadmin=False):
    current_job = None
    if isadmin:
        current_job = session.query(Job).filter(Job.job_id == job_id).first()
    else:
        current_job = session.query(Job).filter(
            Job.owner_id == user_id).filter(Job.job_id == job_id).first()
    if current_job is None:
        return {"session_log": "No permission to get this job's log or cannot found this job's data"}
    if not current_job.work_dir or current_job.work_dir.strip() == "":
        return {"session_log": "No session log found"}

    log_dir = os.path.join(current_job.work_dir, 'log')
    latest_time = None
    latest_file = None
    time_pattern = re.compile(r'time_(\d{14})\.txt$')
    for filename in os.listdir(log_dir):
        match = time_pattern.search(filename)
        if match:
            file_time = datetime.strptime(match.group(1), '%Y%m%d%H%M%S')
            if not latest_time or file_time > latest_time:
                latest_time = file_time
                latest_file = filename

    if not latest_file:
        return {"session_log": "No session log found"}

    # read latest log
    latest_file_path = os.path.join(log_dir, latest_file)
    file_content = ''
    try:
        with open(latest_file_path, 'r') as f:
            file_content = f.read()
    except Exception as e:
        print(f"An exception occurred {e}")
        file_content = "No session log got"
    return {"session_log": file_content}


def create_new_job(job_cfg, user_id, user_name, user_token):
    # replace space to underscore in project name, as the space will lead to job run error
    job = Job(job_name=job_cfg.project_name.replace(" ", "_"), data_source=job_cfg.dataset_path, data_target=job_cfg.export_path,
              repo_id=job_cfg.repo_id, branch=job_cfg.branch,
              status=responses.JOB_STATUS.QUEUED.value, job_type=job_cfg.type, job_source=job_cfg.job_source,
              owner_id=user_id)

    with get_sync_session() as session:
        with session.begin():
            session.add(job)

    if os.getenv("WORKFLOW_ENABLED", "False") == "True":
        from data_server.job.JobWorkflowExecutor import run_executor
        p = Process(target=run_executor, args=(job_cfg, job.job_id,
                                            job.job_name, user_id, user_name, user_token))
        p.start()
    else:
        from data_server.job.JobExecutor import run_executor
        p = Process(target=run_executor, args=(job_cfg, job.job_id,
                                            job.job_name, user_id, user_name, user_token))
        p.start()
    # from data_server.job.JobExecutor import run_executor
    # executor = setup_executor()
    # executor.submit(run_executor, job_cfg, job.job_id,
    #                 job.job_name, user_id, user_name, user_token)

    result = {"job_id": job.job_id,
              "job_name": job.job_name, "status": job.status}

    return result


def delete_job_by_id(id: int, session: Session):
    existing_job = session.query(Job).filter(Job.job_id == id)
    if not existing_job.first():
        return 0
    # delete workdir and input data if the job is defined from repo_id
    try:
        matched_job = existing_job.first()
        if matched_job.repo_id is not None and len(matched_job.repo_id) > 0:
            if len(matched_job.work_dir) > 0 and len(matched_job.data_source) > 0:
                delete_directory_if_exists(matched_job.work_dir)
                delete_directory_if_exists(matched_job.data_source)
            else:
                print(
                    "The attributes 'work_dir' or 'data_source' do not exist in 'matched_job'.")
    except Exception as e:
        print(f'An exception occurred: {e}')

    existing_job.delete(synchronize_session=False)
    session.commit()
    return 1


def search_job(query: str, user_id, session: Session, isadmin=False):
    # if user is supper user, then get all users' jobs
    jobs = []
    # as space job name was replaced with underscore, so we replace query with underscore as well
    query = query.strip().replace(" ", "_")
    if isadmin:
        jobs = session.query(Job).filter(Job.job_name.contains(
            query)).order_by(Job.job_id.desc()).all()
    else:
        jobs = session.query(Job).filter(
            Job.owner_id == user_id).filter(Job.job_name.contains(query)).order_by(Job.job_id.desc()).all()
    return jobs
