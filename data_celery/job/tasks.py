from data_celery.main import celery_app
from data_celery.db.JobsManager import get_pipline_job_by_uid
from data_server.job.JobModels import Job
from sqlalchemy.orm import Session
from data_server.schemas.responses import JOB_STATUS
from data_server.database.session import get_sync_session
from data_celery.utils import (ensure_directory_exists,
                               get_current_ip, get_current_time, get_datasource_temp_parquet_dir,
                               ensure_directory_exists_remove, get_datasource_csg_hub_server_dir)
import traceback
import os,shutil

@celery_app.task(name="run_pipline_job")
def run_pipline_job(job_uuid,user_id, user_name, user_token):
    """
    运行流水线作业的任务。

    Args:
        job_uuid (str): 作业的唯一标识符。
        user_id (int): 用户ID。
        user_name (str): 用户名称。
        user_token (str): 用户令牌。

    Returns:
        None

    """
    # 记录进程ID - redis
    # 读取数据库数据，获取去yaml
    # 获取Job 对象
    job_obj: Job = None
    db_session: Session = None
    try:
        current_ip = get_current_ip()
        db_session: Session = get_sync_session()
        job_obj = get_pipline_job_by_uid(job_uuid)
        job_obj.task_run_host = current_ip

    except Exception as e:
        if job_obj is not None:
            job_obj.status = JOB_STATUS.FAILED.value
        insert_datasource_run_task_log_error(job_uuid, f"Error occurred while executing the task: {e}")
        traceback.print_exc()
        return False
    finally:
        if job_obj:
            job_obj.date_finish = get_current_time()
        if db_session and job_obj:
            db_session.commit()



    # 移出进程ID
    return False

