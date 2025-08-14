import shutil
from data_celery.main import celery_app
import time,os,json
from data_server.database.session import get_sync_session
from sqlalchemy.orm import Session
from data_server.datasource.DatasourceModels import CollectionTask,DataSourceTaskStatusEnum,DataSourceTypeEnum
from data_celery.db.DatasourceManager import get_collection_task_by_uid
from data_celery.utils import (ensure_directory_exists,
                               get_current_ip, get_current_time, get_datasource_temp_parquet_dir,
                               ensure_directory_exists_remove, get_datasource_csg_hub_server_dir)
from data_server.datasource.services.datasource import get_datasource_connector
from data_celery.mongo_tools.tools import insert_datasource_run_task_log_info,insert_datasource_run_task_log_error
from data_engine.exporter.load import load_exporter
from pathlib import Path
import pandas as pd
from loguru import logger


@celery_app.task(name="collection_mongo_task")
def collection_mongo_task(task_uid: str,user_name: str,user_token: str):
    """
    Collection task
    Args:
        task_uid (str): Task UID
        user_name (str): User name
        user_token (str): User token
    Returns:
        bool: Whether the execution operation is successful
    """
    collection_task: CollectionTask = None
    db_session: Session = None
    datasource_temp_parquet_dir = ""
    datasource_csg_hub_server_dir = ""
    try:
        datasource_temp_parquet_dir = get_datasource_temp_parquet_dir(task_uid)
        datasource_csg_hub_server_dir = get_datasource_csg_hub_server_dir(task_uid)
        db_session: Session = get_sync_session()
        insert_datasource_run_task_log_info(task_uid, f"ready the task[{task_uid}]...")
        # Query task information by task_uid
        collection_task: CollectionTask = get_collection_task_by_uid(db_session=db_session, task_uid=task_uid)
        if not collection_task:
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} not found.")
            return False
        # if collection_task.task_status == DataSourceTaskStatusEnum.EXECUTING.value:
        #     insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} is already executing.")
        #     return False
        collection_task.task_status = DataSourceTaskStatusEnum.EXECUTING.value
        insert_datasource_run_task_log_info(task_uid, f"Starting the task[{task_uid}]...")
        db_session.commit()
        ensure_directory_exists_remove(datasource_temp_parquet_dir)
        if not collection_task.datasource:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no associated datasource.")
            return False
        if collection_task.datasource.source_type != DataSourceTypeEnum.MYSQL.value:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} is not a MySQL task.")
            return False
        # Modify the server for task execution
        current_host_ip = get_current_ip()
        if not current_host_ip:
            current_host_ip = "127.0.0.1"
        collection_task.task_run_host = current_host_ip
        collection_task.start_run_at = get_current_time()
        db_session.commit()
        # Read data source
        extra_config = collection_task.datasource.extra_config
        if not extra_config:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no extra configuration.")
            return False
        # Read configuration
        if "mongo" not in extra_config:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no mongo configuration.")
            return False
        mongo_config = extra_config["mongo"]
        max_line = 10000
        csg_hub_dataset_id = 0
        csg_hub_dataset_default_branch = "main"
        if "csg_hub_dataset_default_branch" in extra_config:
            csg_hub_dataset_default_branch = extra_config["csg_hub_dataset_default_branch"]
        if "csg_hub_dataset_id" in extra_config and isinstance(extra_config['csg_hub_dataset_id'], int):
            csg_hub_dataset_id = extra_config["csg_hub_dataset_id"]
        if csg_hub_dataset_id <= 0:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no CSG Hub Dataset ID.")
            return False

        if "max_line_json" in extra_config and isinstance(extra_config['max_line_json'], int):
            max_line = extra_config["max_line_json"]
        if len(mongo_config) == 0:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no mongo configuration.")
            return False
        connector = get_datasource_connector(collection_task.datasource)
        if not connector.test_connection():
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} failed to connect to the database.")
            return False

        total_count = 0
        for collection_name in mongo_config:
            try:
                collection_total = connector.get_collection_document_count(collection_name)
                total_count += collection_total
                collection_task.total_count = total_count
                db_session.commit()
                table_dir = os.path.join(datasource_temp_parquet_dir, collection_name)
                ensure_directory_exists(table_dir)
                page_size = 10000
                page = 1
                current_file_row_count = 0
                records_count = collection_task.records_count
                file_index = 1
                rows_buffer = []  # List for buffering rows
                while True:
                    # Execute pagination query (specific implementation depends on connector details)
                    rows = connector.query_collection(collection_name, offset=(page - 1) * page_size,
                                                 limit=page_size)

                    if not rows:
                        break  # If there is no more data, exit the loop

                    # If the number of rows in the buffer list reaches or exceeds the maximum number of rows, write to the file and clear the buffer list
                    if len(rows_buffer) >= max_line:
                        file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                        df = pd.DataFrame(rows_buffer)
                        df.to_parquet(file_path, index=False)
                        current_file_row_count += len(rows_buffer)
                        records_count += len(rows_buffer)
                        collection_task.records_count = records_count
                        insert_datasource_run_task_log_info(task_uid, f"Task with UID {task_uid} get data count {records_count}...")
                        db_session.commit()
                        file_index += 1
                        rows_buffer = []  # Clear the buffer list
                    page += 1
                # Process the remaining buffered data (if any)
                if rows_buffer:
                    file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                    df = pd.DataFrame(rows_buffer)
                    df.to_parquet(file_path, index=False)
                    current_file_row_count += len(rows_buffer)
                    records_count += len(rows_buffer)
                    collection_task.records_count = records_count
                    insert_datasource_run_task_log_info(task_uid, f"Task with UID {task_uid} get data count {records_count}...")
                    db_session.commit()

            except Exception as e:
                insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} failed to get collection document {collection_name}: {e}")
        collection_task.records_count = total_count
        collection_task.total_count = total_count
        db_session.commit()
        upload_to_csg_hub_server(csg_hub_dataset_id,
                                 csg_hub_dataset_default_branch,
                                 user_name, user_token, db_session,
                                 collection_task, datasource_temp_parquet_dir,
                                 datasource_csg_hub_server_dir)
        collection_task.task_status = DataSourceTaskStatusEnum.COMPLETED.value
        insert_datasource_run_task_log_info(task_uid, f"the task COMPLETED[{task_uid}]...")
    except Exception as e:
        if collection_task:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
        insert_datasource_run_task_log_error(task_uid, f"Error occurred while executing the task: {e}")
        return False
    finally:
        if collection_task:
            collection_task.end_run_at = get_current_time()
        if os.path.exists(datasource_temp_parquet_dir) and not os.path.isdir(datasource_temp_parquet_dir):
            shutil.rmtree(datasource_temp_parquet_dir)
        if os.path.exists(datasource_csg_hub_server_dir) and not os.path.isdir(datasource_csg_hub_server_dir):
            shutil.rmtree(datasource_csg_hub_server_dir)
        if db_session and collection_task:
            db_session.commit()
            db_session.close()
    return True


def upload_to_csg_hub_server(csg_hub_dataset_id: int,
                             csg_hub_dataset_default_branch: str,
                             user_name: str,user_token: str,db_session: Session,
                             collection_task: CollectionTask,datasource_temp_json_dir: str,
                             datasource_csg_hub_server_dir: str):
    """
    Upload to CSG Hub server
    Args:
        csg_hub_dataset_id (int): CSG Hub dataset ID
        csg_hub_dataset_default_branch (str): CSG Hub dataset default branch
        user_name (str): User name
        user_token (str): User token
        db_session (Session): Database session
        collection_task (CollectionTask): Collection task
        datasource_temp_json_dir (str): Data source temporary json file directory
    Returns:
        None
    """
    try:
        # Upload to CSG Hub server

        ensure_directory_exists_remove(datasource_csg_hub_server_dir)
        insert_datasource_run_task_log_info(collection_task.task_uid, f"Starting upload csg hub-server the task[{collection_task.task_uid}]...")
        exporter = load_exporter(
            export_path=datasource_temp_json_dir,
            repo_id=str(csg_hub_dataset_id),
            branch=csg_hub_dataset_default_branch,
            user_name=user_name,
            user_token=user_token,
            work_dir=datasource_csg_hub_server_dir
        )
        upload_path: Path = Path(datasource_csg_hub_server_dir)
        output_branch_name = exporter.export_from_files(upload_path)

        if output_branch_name:
            collection_task.csg_hub_branch = output_branch_name
            db_session.commit()
            insert_datasource_run_task_log_info(collection_task.task_uid, f"the task[{collection_task.task_uid}] upload csg hub-server success...")
        else:
            insert_datasource_run_task_log_error(collection_task.task_uid, f"the task[{collection_task.task_uid}] upload csg hub-server fail...")
    except Exception as e:
        logger.error(e)
        insert_datasource_run_task_log_error(collection_task.task_uid,f"Task UID {collection_task.task_uid} Error occurred while uploading to CSG Hub server: {e}")
        return False
    return True
