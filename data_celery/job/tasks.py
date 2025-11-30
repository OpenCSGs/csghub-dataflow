from data_celery.main import celery_app
from data_celery.db.JobsManager import get_pipline_job_by_uid
from data_server.job.JobModels import Job
from sqlalchemy.orm import Session
from data_server.schemas.responses import JOB_STATUS
from data_server.database.session import get_sync_session
from data_celery.utils import (ensure_directory_exists,
                               get_current_ip, get_current_time, get_pipline_temp_job_dir,
                               ensure_directory_exists_remove, get_datasource_csg_hub_server_dir)
from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_error, insert_pipline_job_run_task_log_info
from data_server.database.session import (get_celery_worker_redis_db,get_celery_task_process_real_key,
                                          get_celery_process_list_key)
from data_engine.utils.env import GetDataTopPath
import os,shutil,yaml
from data_server.logic.models  import Recipe
from data_server.logic.utils import exclude_fields_config
from data_engine.config import init_configs
from data_engine.core import Executor
import tempfile,time
import traceback
import io
from loguru import logger


@celery_app.task(name="run_pipline_job")
def run_pipline_job(job_uuid,user_id, user_name, user_token):
    job_obj: Job = None
    db_session: Session = None
    current_ip = None
    current_process_id = 0
    yaml_temp_dir = None
    work_name = None
    try:
        db_session = get_sync_session()
        job_celery_uuid = ""
        for i in range(10):
            job_obj = get_pipline_job_by_uid(db_session, job_uuid)
            if job_obj is not None and job_obj.job_celery_uuid is not None and job_obj.job_celery_uuid != "":
                job_celery_uuid = job_obj.job_celery_uuid
                break
            time.sleep(1)
        if job_celery_uuid == "":
            insert_pipline_job_run_task_log_error(job_uuid, f"not found job celery uuid : {job_uuid}")
            return False
        job_obj = get_pipline_job_by_uid(db_session, job_uuid)
        if job_obj is None:
            insert_pipline_job_run_task_log_error(job_uuid, f"not found job uuid : {job_uuid}")
            return False

        current_ip = get_current_ip()
        work_name = get_worker_for_task(celery_app,job_celery_uuid)
        if work_name is None:
            job_obj.status = JOB_STATUS.FAILED.value
            insert_pipline_job_run_task_log_error(job_uuid, f"not found work name : {job_uuid}")
            return False
        current_process_id = os.getpid()
        add_process_to_redis(job_uuid,current_process_id, current_ip,work_name)
        # for i in range(100000):
        #     print(f"任务进行中:{i}")
        #     time.sleep(1)

        job_obj.task_run_host = current_ip
        job_obj.job_celery_work_name = work_name
        db_session.commit()
        yaml_temp_dir = get_pipline_temp_job_dir(job_uuid)
        ensure_directory_exists(yaml_temp_dir)
        yaml_content = job_obj.yaml_config
        yaml_full_path = os.path.join(yaml_temp_dir, f"{job_uuid}.yaml")
        string_io = io.StringIO(yaml_content)
        string_io.name = yaml_full_path
        recipe_model: Recipe = Recipe.parse_yaml(string_io)
        if recipe_model is not None:
            data_path = os.path.join(GetDataTopPath(), job_obj.job_name + "_" + job_obj.uuid)
            dataset_path = os.path.join(data_path, 'input')
            export_path = os.path.join(data_path, 'output', '_df_dataset.jsonl')
            recipe_model.dataset_path = dataset_path
            recipe_model.export_path = export_path
            # print("recipe_model.dataset_path",dataset_path)
            # print("recipe_model.export_path", export_path)
            run_pipline_job_task(recipe_model, job_obj, db_session, user_id, user_name, user_token)
            return True
        else:
            job_obj.status = JOB_STATUS.FAILED.value
            insert_pipline_job_run_task_log_error(job_uuid, f"not parse yaml config : {job_uuid}")
            return False
        # with open(yaml_full_path, 'w') as file:
        #     yaml.dump(yaml_content, file, default_flow_style=False, allow_unicode=True)
        # if os.path.exists(yaml_full_path):
        #
        # else:
        #     job_obj.status = JOB_STATUS.FAILED.value
        #     insert_pipline_job_run_task_log_error(job_uuid, f"not exists yaml config : {job_uuid}")
        #     return False
    except Exception as e:
        if job_obj is not None and db_session:
            try:
                # 确保任务状态被正确更新为 FAILED
                job_obj.status = JOB_STATUS.FAILED.value
                job_obj.date_finish = get_current_time()
                db_session.flush()  # 先 flush 确保更改被记录
                db_session.commit()  # 然后 commit 确保持久化
            except Exception as db_error:
                logger.error(f"Failed to update job status to FAILED in outer exception handler: {db_error}")
                try:
                    db_session.rollback()
                    # 重新查询 job 对象
                    job_obj_refreshed = get_pipline_job_by_uid(db_session, job_uuid)
                    if job_obj_refreshed:
                        job_obj_refreshed.status = JOB_STATUS.FAILED.value
                        job_obj_refreshed.date_finish = get_current_time()
                        db_session.commit()
                except Exception as e2:
                    logger.error(f"Failed to update job status even after rollback: {e2}")
        insert_pipline_job_run_task_log_error(job_uuid, f"{job_uuid} Error occurred while executing the task: {e.__str__()}")
        traceback.print_exc()
        return False
    finally:
        if job_obj and db_session:
            try:
                # 确保完成时间被设置（如果之前没有设置）
                if not job_obj.date_finish:
                    job_obj.date_finish = get_current_time()
                # 如果状态还是 PROCESSING，说明异常处理可能没有正确执行，设置为 FAILED
                if job_obj.status == JOB_STATUS.PROCESSING.value:
                    job_obj.status = JOB_STATUS.FAILED.value
                db_session.commit()
            except Exception as e:
                logger.error(f"Failed to update job in finally block: {e}")
            finally:
                db_session.close()
        # if yaml_temp_dir and os.path.exists(yaml_temp_dir) and os.path.isdir(yaml_temp_dir):
        #     shutil.rmtree(yaml_temp_dir)
        if current_process_id > 0 and current_ip is not None and work_name is not None:
            remove_process_from_redis(job_uuid,current_process_id, current_ip,work_name)


def get_worker_for_task(app, task_id):
    inspector = app.control.inspect()

    active_tasks = inspector.active()
    if not active_tasks:
        return None

    for worker_name, tasks in active_tasks.items():
        for task in tasks:
            if task['id'] == task_id:
                return worker_name
    return None

def add_process_to_redis(job_uuid,process_id, current_ip,work_name):
    redis_process_key = get_celery_process_list_key(work_name,current_ip)
    redis_celery = get_celery_worker_redis_db()
    all_elements = redis_celery.lrange(redis_process_key, 0, -1)
    if str(process_id) not in [str(element) for element in all_elements]:
        redis_celery.lpush(redis_process_key, f"{job_uuid}:{str(process_id)}")

    celery_task_process_real_key = get_celery_task_process_real_key(job_uuid)
    redis_celery.set(celery_task_process_real_key, str(process_id))

def remove_process_from_redis(job_uuid,process_id, current_ip,work_name):
    redis_process_key = get_celery_process_list_key(work_name,current_ip)
    redis_celery = get_celery_worker_redis_db()
    redis_celery.lrem(redis_process_key, 0, f"{job_uuid}:{str(process_id)}")
    celery_task_process_real_key = get_celery_task_process_real_key(job_uuid)
    redis_celery.delete(celery_task_process_real_key)

def run_pipline_job_task(config,job,session,user_id, user_name, user_token):
    """
    pipline task。
    """
    repo_id = config.repo_id
    work_dir = os.path.dirname(config.export_path)
    config.branch = config.branch if config.branch and len(config.branch) > 0 else 'main'
    # handle pipeline jobs:
    yaml_content = config.yaml(exclude=exclude_fields_config)
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmpfile:
        tmpfile.write(yaml_content)
        temp_dir_str = tmpfile.name

    try:
        cfg = init_configs(['--config', temp_dir_str, '--user_id', user_id,
                            '--user_name', user_name, '--user_token', user_token], redirect=False)
    except:
        insert_pipline_job_run_task_log_error(job.uuid, f"{job.uuid} :Config initialization failed")
        raise

    # return
    temp_filename = os.path.basename(temp_dir_str)

    work_dir = cfg.work_dir
    temp_work_file = os.path.join(work_dir, temp_filename)
    config_file = os.path.join(work_dir, 'config.yaml')
    try:
        os.remove(temp_dir_str)  # Delete temp file
        os.remove(temp_work_file)
    except FileNotFoundError:
        insert_pipline_job_run_task_log_error(job.uuid, f"{job.uuid} :not exists yaml config - {temp_work_file}")
        raise
    except PermissionError:
        insert_pipline_job_run_task_log_error(job.uuid, f"{job.uuid} :Permission denied. You cannot remove - {temp_work_file}")
        raise

    with open(config_file, mode='w') as file:
        file.write(config.yaml())
    executor = Executor(cfg,job_uid=job.uuid)
    job.data_source = config.dataset_path
    job.data_target = config.export_path
    job.work_dir = work_dir
    job.status = JOB_STATUS.PROCESSING.value
    session.commit()
    try:
        _, branch_name = executor.run()

        trace_dir = os.path.join(work_dir, 'trace')
        first_op = list(cfg.process[0])[0]
        count_filename = f"count-{first_op}.txt"
        count_filepath = os.path.join(trace_dir, count_filename)
        data_count = 0
        if os.path.exists(count_filepath):
            with open(count_filepath, 'r') as f:
                data_lines = f.read().strip()
                data_count = int(data_lines) if data_lines else 0

        job.data_count = data_count
        job.status = JOB_STATUS.FINISHED.value
        job.process_count = data_count
        job.export_repo_id = repo_id
        job.export_branch_name = branch_name
        session.commit()
    except Exception as e:
        # 当操作符执行失败时，确保任务状态被正确更新为 FAILED
        try:
            # 使用 flush 和 commit 确保状态被正确保存
            job.status = JOB_STATUS.FAILED.value
            job.date_finish = get_current_time()
            session.flush()  # 先 flush 确保更改被记录
            session.commit()  # 然后 commit 确保持久化
        except Exception as db_error:
            # 如果更新失败，记录错误但继续抛出原始异常
            logger.error(f"Failed to update job status to FAILED: {db_error}")
            # 尝试回滚并重新提交
            try:
                session.rollback()
                from data_celery.db.JobsManager import get_pipline_job_by_uid
                job_from_db = get_pipline_job_by_uid(session, job.uuid)
                if job_from_db:
                    job_from_db.status = JOB_STATUS.FAILED.value
                    job_from_db.date_finish = get_current_time()
                    session.commit()
            except Exception as e2:
                logger.error(f"Failed to update job status even after rollback: {e2}")
        insert_pipline_job_run_task_log_error(job.uuid, f"{job.uuid} Error occurred during pipeline execution: {str(e)}")
        raise