import shutil
import traceback

from data_celery.main import celery_app
import time,os,json
from data_server.database.session import get_sync_session
from sqlalchemy.orm import Session
from data_server.datasource.DatasourceModels import CollectionTask,DataSourceTaskStatusEnum,DataSourceTypeEnum
from data_celery.db.DatasourceManager import get_collection_task_by_uid
from data_celery.utils import (ensure_directory_exists,
                               get_current_ip, get_current_time, get_datasource_temp_parquet_dir,
                               ensure_directory_exists_remove, get_datasource_csg_hub_server_dir)
from data_celery.mongo_tools.tools import insert_datasource_run_task_log_info,insert_datasource_run_task_log_error
from data_server.datasource.services.datasource import get_datasource_connector
from data_server.datasource.schemas import DataSourceCreate
from data_engine.exporter.load import load_exporter
from pathlib import Path
import pandas as pd
from loguru import logger

@celery_app.task(name="collection_hive_task")
def collection_hive_task(task_uid: str,user_name: str,user_token: str):
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
        collection_task.start_run_at = get_current_time()
        insert_datasource_run_task_log_info(task_uid, f"Starting the task[{task_uid}]...")
        collection_task.start_run_at = get_current_time()
        db_session.commit()
        ensure_directory_exists_remove(datasource_temp_parquet_dir)
        if not collection_task.datasource:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no associated datasource.")
            return False
        if collection_task.datasource.source_type != DataSourceTypeEnum.HIVE.value:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} is not a HIVE task.")
            return False
        current_host_ip = get_current_ip()
        if not current_host_ip:
            current_host_ip = "127.0.0.1"
        collection_task.task_run_host = current_host_ip
        collection_task.start_run_at = get_current_time()
        db_session.commit()
        extra_config = json.loads(collection_task.datasource.extra_config)
        if not extra_config:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no extra configuration.")
            return False
        if "hive" not in extra_config:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no HIVE configuration.")
            return False
        hive_config = extra_config["hive"]
        use_type = ""
        use_sql = ""
        max_line = 10000
        csg_hub_dataset_id = ""
        csg_hub_dataset_default_branch = "main"
        if "type" in hive_config:
            use_type = hive_config["type"]
        if "sql" in hive_config:
            use_sql = hive_config["sql"]
        if "csg_hub_dataset_default_branch" in extra_config:
            csg_hub_dataset_default_branch = extra_config["csg_hub_dataset_default_branch"]
        if "csg_hub_dataset_name" in extra_config and extra_config['csg_hub_dataset_name'] != '':
            csg_hub_dataset_name = extra_config["csg_hub_dataset_name"]
        else:
            csg_hub_dataset_name = csg_hub_dataset_default_branch
        if "csg_hub_dataset_id" in extra_config:
            csg_hub_dataset_id = extra_config["csg_hub_dataset_id"]
        if csg_hub_dataset_name is None or csg_hub_dataset_name == '':
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no CSG Hub Dataset Name.")
        if csg_hub_dataset_id is None or csg_hub_dataset_id == "":
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no CSG Hub Dataset ID.")
            return False
        if "max_line_json" in extra_config and isinstance(extra_config['max_line_json'], int):
            max_line = extra_config["max_line_json"]
        if use_type == "sql":
            if use_sql:
                try:
                    # Convert database object to DataSourceCreate object
                    datasource_create = DataSourceCreate(
                        name=collection_task.datasource.name,
                        des=collection_task.datasource.des,
                        source_type=collection_task.datasource.source_type,
                        host=collection_task.datasource.host,
                        port=collection_task.datasource.port,
                        username=collection_task.datasource.username,
                        password=collection_task.datasource.password,
                        database=collection_task.datasource.database,
                        auth_type=collection_task.datasource.auth_type
                    )
                    connector = get_datasource_connector(datasource_create)
                    test_result = connector.test_connection()
                    if not test_result or not test_result.get("success", False):
                        collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                        error_msg = test_result.get("message", "Connection failed") if test_result else "Connection test returned None"
                        insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} failed to connect to the database: {error_msg}")
                        return False
                    get_table_dataset_by_sql(connector, task_uid, use_sql, db_session, collection_task,
                                             datasource_temp_parquet_dir, max_line=max_line)
                except Exception as e:
                    collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                    insert_datasource_run_task_log_error(task_uid, f"Error occurred while executing the task: {str(e)}")
                    return False
                upload_path = datasource_temp_parquet_dir.join('run_sql')
                upload_to_csg_hub_server(csg_hub_dataset_id,
                                         csg_hub_dataset_name,
                                         user_name, user_token, db_session,
                                         collection_task, upload_path,
                                         datasource_csg_hub_server_dir)
            else:
                collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no SQL configuration.")
                return False
        else:
            if "source" in hive_config:
                source = hive_config["source"]
                total_count = 0
                records_count = 0
                try:
                    # Convert database object to DataSourceCreate object
                    datasource_create = DataSourceCreate(
                        name=collection_task.datasource.name,
                        des=collection_task.datasource.des,
                        source_type=collection_task.datasource.source_type,
                        host=collection_task.datasource.host,
                        port=collection_task.datasource.port,
                        username=collection_task.datasource.username,
                        password=collection_task.datasource.password,
                        database=collection_task.datasource.database,
                        auth_type=collection_task.datasource.auth_type
                    )
                    connector = get_datasource_connector(datasource_create)
                    test_result = connector.test_connection()
                    if not test_result or not test_result.get("success", False):
                        collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                        error_msg = test_result.get("message", "Connection failed") if test_result else "Connection test returned None"
                        insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} failed to connect to the database: {error_msg}")
                        return False
                    for table_name in source.keys():
                        table_total = connector.get_table_total_count_hive(table_name)
                        total_count += table_total
                except Exception as e:
                    collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                    insert_datasource_run_task_log_error(task_uid, f"Error occurred while executing the task: {str(e)}")
                    return False
                
                collection_task.total_count = total_count
                collection_task.records_count = records_count
                db_session.commit()
                for table_name in source.keys():
                    config_columns = source[table_name]
                    get_table_dataset(connector, task_uid, db_session, collection_task, table_name,
                                      config_columns, datasource_temp_parquet_dir, max_line=max_line)
                    table_path = os.path.join(datasource_temp_parquet_dir, table_name)
                    if not os.path.exists(table_path):
                        continue
                    files = os.listdir(table_path)
                    for file in files:
                        if not os.path.isdir(file):
                            inner_path = os.path.join(table_path, table_name)
                            ensure_directory_exists(inner_path)
                            shutil.move(os.path.join(table_path, file), os.path.join(inner_path, file))
                    upload_to_csg_hub_server(csg_hub_dataset_id,
                                             csg_hub_dataset_name,
                                             user_name, user_token, db_session,
                                             collection_task, table_path,
                                             datasource_csg_hub_server_dir)
                collection_task.records_count = total_count
            else:
                collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no source configuration.")
                return False
        collection_task.task_status = DataSourceTaskStatusEnum.COMPLETED.value
        insert_datasource_run_task_log_info(task_uid, f"the task COMPLETED[{task_uid}]...")
        return True
    except Exception as e:
        if collection_task:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
        error_type = type(e).__name__
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        logger.error(f"Task {task_uid} error: {error_type}: {error_msg}")
        logger.error(f"Full traceback:\n{error_traceback}")
        traceback.print_exc()
        insert_datasource_run_task_log_error(task_uid, f"Error occurred while executing the task: {error_type}: {error_msg}")
        insert_datasource_run_task_log_error(task_uid, f"Traceback: {error_traceback}")
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


def upload_to_csg_hub_server(csg_hub_dataset_id: str,
                             csg_hub_dataset_default_branch: str,
                             user_name: str, user_token: str, db_session: Session,
                             collection_task: CollectionTask, datasource_temp_json_dir: str,
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
            repo_id=csg_hub_dataset_id,
            branch=csg_hub_dataset_default_branch,
            user_name=user_name,
            user_token=user_token,
            work_dir=datasource_csg_hub_server_dir,
            path_is_dir=True
        )
        exporter.export_large_folder()
        if csg_hub_dataset_default_branch:
            collection_task.csg_hub_branch = csg_hub_dataset_default_branch
            db_session.commit()
            insert_datasource_run_task_log_info(collection_task.task_uid, f"the task[{collection_task.task_uid}] upload csg hub-server success...")
        else:
            insert_datasource_run_task_log_error(collection_task.task_uid, f"the task[{collection_task.task_uid}] upload csg hub-server fail...")
    except Exception as e:
        logger.error(e)
        insert_datasource_run_task_log_error(collection_task.task_uid,
                  f"Task UID {collection_task.task_uid} Error occurred while uploading to CSG Hub server: {e}")
        return False
    return True


def get_table_dataset(connector,task_uid: str, db_session: Session,
                      collection_task: CollectionTask, table_name: str,
                      config_columns: list, base_dir: str, max_line: int = 10000) -> None:
    """
    Get dataset of the table
    Args:
        connector: Database connector
        task_uid (str): Task UID
        db_session (Session): Database session
        collection_task (CollectionTask): Collection task
        table_name (str): Table name
        config_columns (list): List of configured column names
        base_dir (str): Base directory
        max_line (int): Maximum number of lines per file
    Returns:
        None
    """

    try:
        real_get_columns = []
        columns = connector.get_table_columns(table_name)
        logger.info(f'列：{columns}')
        if config_columns:
            for column in config_columns:
                if column in columns:
                    real_get_columns.append(column)
        if len(real_get_columns) == 0:
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} Table {table_name} has no valid columns.")
            return
        table_dir = os.path.join(base_dir, table_name)
        ensure_directory_exists(table_dir)
        page_size = 10000
        page = 1
        current_file_row_count = 0
        records_count = collection_task.records_count
        file_index = 1
        rows_buffer = []
        while True:
            rows = connector.query_table_hive(table_name, real_get_columns, offset=(page - 1) * page_size,
                                         limit=page_size)
            if not rows:
                break
            rows_buffer.extend(rows)
            if len(rows_buffer) >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                df = pd.DataFrame(rows_buffer)
                df.to_parquet(file_path, index=False)
                current_file_row_count += len(rows_buffer)
                records_count += len(rows_buffer)
                collection_task.records_count = records_count
                insert_datasource_run_task_log_info(task_uid, f"Task with UID {task_uid} get data count {records_count}...")
                db_session.commit()
                rows_buffer = []
                file_index += 1
            page += 1
        if rows_buffer:
            file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
            df = pd.DataFrame(rows_buffer)
            df.to_parquet(file_path, index=False)
            current_file_row_count += len(rows_buffer)
            records_count += len(rows_buffer)
            collection_task.records_count = records_count
            insert_datasource_run_task_log_info(task_uid, f"Task with UID {task_uid} get data count {records_count}...")
            db_session.commit()
        insert_datasource_run_task_log_info(task_uid, f"Task with UID {task_uid} get data count {collection_task.records_count}...")
    except Exception as e:
        traceback.print_exc()
        insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} Error occurred while getting table dataset: {e}")


def get_table_dataset_by_sql(connector, task_uid: str, run_sql: str,
                             db_session: Session, collection_task: CollectionTask,
                             base_dir: str, max_line: int = 10000):
    """
    Obtain the dataset of the table through the specified SQL
    Args:
        connector: Database connector
        task_uid (str): Task UID
        run_sql (str): SQL to execute
        db_session (Session): Database session
        collection_task (CollectionTask): Collection task
        base_dir (str): Base directory
        max_line (int): Maximum number of lines per file
    Returns:
        None
    """
    try:
        # A single table is also placed in a separate folder
        table_dir = os.path.join(base_dir, "run_sql")
        ensure_directory_exists(table_dir)
        rows = connector.execute_custom_query_hive(run_sql)
        if not rows:
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} No results returned from SQL query.")
            return
        # Initialize file index and current file record count
        file_index = 1
        current_file_row_count = 0
        total_rows = 0
        rows_list = []
        # Iterate through the query results and write to the file
        for row in rows:
            # Add rows to DataFrame
            # If the number of rows in the current file reaches the limit, write to the file and reset the counter
            if current_file_row_count >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                df_to_write = pd.DataFrame(rows_list[:max_line])
                df_to_write.to_parquet(file_path, index=False)
                file_index += 1
                current_file_row_count = 0
                rows_list = []
            # Add the current row to the list of rows to be written
            rows_list.append(row)
            current_file_row_count += 1
            total_rows += 1
            # Update the current file record count
            current_file_row_count += 1
            if current_file_row_count % 10000 == 0:
                collection_task.records_count = current_file_row_count
                db_session.commit()
                insert_datasource_run_task_log_info(task_uid, f"Task with UID {task_uid} get data count {current_file_row_count}...")
        if len(rows_list) > 0:
            file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
            df_to_write = pd.DataFrame(rows_list)
            df_to_write.to_parquet(file_path, index=False)
        collection_task.total_count = len(rows)
        collection_task.records_count = len(rows)
        db_session.commit()
        insert_datasource_run_task_log_info(task_uid, f"Task with UID {task_uid} get data count {collection_task.records_count}...")
    except Exception as e:
        insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} Error occurred while getting table dataset: {e}")

