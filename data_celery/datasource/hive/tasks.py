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
from data_celery.mongo_tools.tools import insert_datasource_run_task_log_info,insert_datasource_run_task_log_error
from data_server.datasource.services.datasource import get_datasource_connector
from data_engine.exporter.load import load_exporter
from pathlib import Path
import pandas as pd
from loguru import logger

@celery_app.task(name="collection_hive_task")
def collection_hive_task(task_uid: str,user_name: str,user_token: str):
    """
    采集任务
    Args:
        task_uid (str): 任务UID
        user_name (str): 用户名称
        user_token (str): 用户token
    Returns:
        bool: 执行操作是否成功
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
        # 根据 task_uid 查询出任务信息
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
        # 修改任务执行的服务器
        current_host_ip = get_current_ip()
        if not current_host_ip:
            current_host_ip = "127.0.0.1"
        collection_task.task_run_host = current_host_ip
        collection_task.start_run_at = get_current_time()
        db_session.commit()
        # 读取数据源
        extra_config = json.loads(collection_task.datasource.extra_config)
        if not extra_config:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no extra configuration.")
            return False
        # 读取配置
        if "hive" not in extra_config:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no MySQL configuration.")
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
        if "csg_hub_dataset_id" in extra_config and isinstance(extra_config['csg_hub_dataset_id'], int):
            csg_hub_dataset_id = extra_config["csg_hub_dataset_id"]
        if csg_hub_dataset_id <= 0:
            collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no CSG Hub Dataset ID.")
            return False

        if "max_line_json" in extra_config and isinstance(extra_config['max_line_json'], int):
            max_line = extra_config["max_line_json"]
        if use_type == "sql":
            # 执行SQL语句 获取数据
            if use_sql:
                connector = get_datasource_connector(collection_task.datasource)
                if not connector.test_connection():
                    collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                    insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} failed to connect to the database.")
                    return False
                get_table_dataset_by_sql(connector, task_uid, use_sql, db_session, collection_task,
                                         datasource_temp_parquet_dir, max_line=max_line)
            else:
                collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no SQL configuration.")
                return False
        else:
            # 根据mysql_config 获取数据
            if "source" in hive_config:
                source = hive_config["source"]
                # 先收集 所有表的 total
                total_count = 0
                records_count = 0
                connector = get_datasource_connector(collection_task.datasource)
                if not connector.test_connection():
                    collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                    insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} failed to connect to the database.")
                    return False
                for table_name in source.keys():
                    table_total = connector.get_table_total_count_hive(table_name)
                    total_count += table_total

                collection_task.total_count = total_count
                collection_task.records_count = records_count
                db_session.commit()
                # 循环获取数据
                for table_name in source.keys():
                    config_columns = source[table_name]
                    get_table_dataset(connector, task_uid, db_session, collection_task, table_name,
                                      config_columns, datasource_temp_parquet_dir, max_line=max_line)
                collection_task.records_count = total_count
            else:
                collection_task.task_status = DataSourceTaskStatusEnum.ERROR.value
                insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} has no source configuration.")
                return False
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


def upload_to_csg_hub_server(csg_hub_dataset_id: str,
                             csg_hub_dataset_default_branch: str,
                             user_name: str, user_token: str, db_session: Session,
                             collection_task: CollectionTask, datasource_temp_json_dir: str,
                             datasource_csg_hub_server_dir: str):
    """
    上传到CSG Hub服务器
    Args:
        csg_hub_dataset_id (int): CSG Hub数据集ID
        csg_hub_dataset_default_branch (str): CSG Hub数据集默认分支
        user_name (str): 用户名称
        user_token (str): 用户token
        db_session (Session): 数据库会话
        collection_task (CollectionTask): 采集任务
        datasource_temp_json_dir (str): 数据源临时json文件目录
    Returns:
        None
    """
    try:
        # 上传到CSG Hub服务器
        ensure_directory_exists_remove(datasource_csg_hub_server_dir)
        insert_datasource_run_task_log_info(collection_task.task_uid, f"Starting upload csg hub-server the task[{collection_task.task_uid}]...")
        exporter = load_exporter(
            export_path=datasource_temp_json_dir,
            repo_id=csg_hub_dataset_id,
            branch=csg_hub_dataset_default_branch,
            user_name=user_name,
            user_token=user_token,
            work_dir=datasource_csg_hub_server_dir
        )
        upload_path: Path = Path(datasource_temp_json_dir)
        output_branch_name = exporter.export_from_files(upload_path)

        if output_branch_name:
            collection_task.csg_hub_branch = output_branch_name
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
    获取表的数据集
    Args:
        connector: 数据库连接器
        task_uid (str): 任务UID
        db_session (Session): 数据库会话
        collection_task (CollectionTask): 采集任务
        table_name (str): 表名
        config_columns (list): 配置的列名列表
        base_dir (str): 基础目录
        max_line (int): 每个文件的最大行数
    Returns:
        None
    """

    try:
        # 获取当前所有的列表，取到真实的列名
        real_get_columns = []
        columns = connector.get_table_columns(table_name)
        if config_columns:
            for column in config_columns:
                columns_name_list = [item['column_name'] for item in columns]
                if column in columns_name_list:
                    real_get_columns.append(column)
        if len(real_get_columns) == 0:
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} Table {table_name} has no valid columns.")
            return
        # 单张table 也是放到单独的文件夹下
        table_dir = os.path.join(base_dir, table_name)
        ensure_directory_exists(table_dir)
        page_size = 10000
        page = 1
        current_file_row_count = 0
        records_count = collection_task.records_count
        file_index = 1
        rows_buffer = []  # 用于缓冲行的列表
        while True:
            # 执行分页查询（具体实现取决于connector的实现细节）
            rows = connector.query_table_hive(table_name, real_get_columns, offset=(page - 1) * page_size,
                                         limit=page_size)

            if not rows:
                break  # 如果没有更多数据，则退出循环

            # 将查询结果添加到缓冲列表中
            rows_buffer.extend(rows)
            # 如果缓冲列表中的行数达到或超过最大行数，则写入文件并清空缓冲列表
            if len(rows_buffer) >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                df = pd.DataFrame(rows_buffer)
                df.to_parquet(file_path, index=False)
                current_file_row_count += len(rows_buffer)
                records_count += len(rows_buffer)
                collection_task.records_count = records_count
                insert_datasource_run_task_log_info(task_uid, f"Task with UID {task_uid} get data count {records_count}...")
                db_session.commit()
                rows_buffer = []  # 清空缓冲列表
                file_index += 1
            # 处理剩余的缓冲数据（如果有）
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
        insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} Error occurred while getting table dataset: {e}")


def get_table_dataset_by_sql(connector, task_uid: str, run_sql: str,
                             db_session: Session, collection_task: CollectionTask,
                             base_dir: str, max_line: int = 10000):
    """
    通过指定的sql获取表的数据集
    Args:
        connector: 数据库连接器
        task_uid (str): 任务UID
        run_sql (str): 执行sql
        db_session (Session): 数据库会话
        collection_task (CollectionTask): 采集任务
        base_dir (str): 基础目录
        max_line (int): 每个文件的最大行数
    Returns:
        None
    """
    try:
        # 单张table 也是放到单独的文件夹下
        table_dir = os.path.join(base_dir, "run_sql")
        ensure_directory_exists(table_dir)
        rows = connector.execute_custom_query_hive(run_sql)
        if not rows:
            insert_datasource_run_task_log_error(task_uid, f"Task with UID {task_uid} No results returned from SQL query.")
            return
        # 初始化文件索引和当前文件记录数
        file_index = 1
        current_file_row_count = 0
        total_rows = 0
        rows_list = []
        # 遍历查询结果并写入文件
        for row in rows:
            # 将行添加到DataFrame中
            # 如果当前文件行数达到限制，则写入文件并重置计数器
            if current_file_row_count >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                df_to_write = pd.DataFrame(rows_list[:max_line])
                df_to_write.to_parquet(file_path, index=False)
                file_index += 1
                current_file_row_count = 0
                rows_list = []
            # 将当前行添加到待写入的行列表中
            rows_list.append(row)
            current_file_row_count += 1
            total_rows += 1
            # 更新当前文件记录数
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

