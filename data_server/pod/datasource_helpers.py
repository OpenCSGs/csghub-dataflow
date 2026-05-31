import os
import traceback
from datetime import date, datetime

import pandas as pd
from loguru import logger

from data_server.pod.pod_logger import log_task_error, log_task_info

try:
    from bson import ObjectId

    BSON_AVAILABLE = True
except ImportError:
    BSON_AVAILABLE = False
    ObjectId = None


def convert_mongo_document(doc):
    if isinstance(doc, dict):
        return {key: convert_mongo_document(value) for key, value in doc.items()}
    if isinstance(doc, list):
        return [convert_mongo_document(item) for item in doc]
    if BSON_AVAILABLE and isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, (datetime, date)):
        return doc.isoformat()
    return doc


def mysql_get_table_dataset(
    connector,
    task_uid: str,
    collection_task,
    table_name: str,
    config_columns: list,
    base_dir: str,
    max_line: int = 10000,
) -> None:
    try:
        real_get_columns = []
        columns = connector.get_table_columns(table_name)
        if config_columns:
            for column in config_columns:
                columns_name_list = [item["column_name"] for item in columns]
                if column in columns_name_list:
                    real_get_columns.append(column)
        if len(real_get_columns) == 0:
            log_task_error(
                task_uid,
                f"Task with UID {task_uid} Table {table_name} has no valid columns.",
            )
            return

        table_dir = os.path.join(base_dir, table_name)
        os.makedirs(table_dir, exist_ok=True)
        page_size = 10000
        page = 1
        records_count = collection_task.records_count or 0
        file_index = 1
        rows_buffer = []
        while True:
            rows = connector.query_table(
                table_name,
                real_get_columns,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            if not rows:
                break
            rows_buffer.extend(rows)
            if len(rows_buffer) >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                pd.DataFrame(rows_buffer).to_parquet(file_path, index=False)
                records_count += len(rows_buffer)
                collection_task.records_count = records_count
                log_task_info(
                    task_uid,
                    f"Task with UID {task_uid} get data count {records_count}...",
                )
                rows_buffer = []
                file_index += 1
            page += 1
        if rows_buffer:
            file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
            pd.DataFrame(rows_buffer).to_parquet(file_path, index=False)
            records_count += len(rows_buffer)
            collection_task.records_count = records_count
            log_task_info(
                task_uid,
                f"Task with UID {task_uid} get data count {records_count}...",
            )
        log_task_info(
            task_uid,
            f"Task with UID {task_uid} get data count {collection_task.records_count}...",
        )
    except Exception as e:
        log_task_error(
            task_uid,
            f"Task with UID {task_uid} Error occurred while getting table dataset: {e}",
        )
        traceback.print_exc()


def mysql_get_table_dataset_by_sql(
    connector,
    task_uid: str,
    run_sql: str,
    collection_task,
    base_dir: str,
    max_line: int = 10000,
):
    try:
        table_dir = os.path.join(base_dir, "run_sql")
        os.makedirs(table_dir, exist_ok=True)
        rows = connector.execute_custom_query(run_sql)
        if not rows:
            log_task_error(
                task_uid,
                f"Task with UID {task_uid} No results returned from SQL query.",
            )
            return
        file_index = 1
        current_file_row_count = 0
        rows_list = []
        for row in rows:
            if current_file_row_count >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                pd.DataFrame(rows_list[:max_line]).to_parquet(file_path, index=False)
                file_index += 1
                current_file_row_count = 0
                rows_list = []
            rows_list.append(row)
            current_file_row_count += 1
            current_file_row_count += 1
            if current_file_row_count % 10000 == 0:
                collection_task.records_count = current_file_row_count
                log_task_info(
                    task_uid,
                    f"Task with UID {task_uid} get data count {current_file_row_count}...",
                )
        if len(rows_list) > 0:
            file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
            pd.DataFrame(rows_list).to_parquet(file_path, index=False)
        collection_task.total_count = len(rows)
        collection_task.records_count = len(rows)
        log_task_info(
            task_uid,
            f"Task with UID {task_uid} get data count {collection_task.records_count}...",
        )
    except Exception as e:
        log_task_error(
            task_uid,
            f"Task with UID {task_uid} Error occurred while getting table dataset: {e}",
        )


def hive_get_table_dataset(
    connector,
    task_uid: str,
    collection_task,
    table_name: str,
    config_columns: list,
    base_dir: str,
    max_line: int = 10000,
) -> None:
    try:
        real_get_columns = []
        columns = connector.get_table_columns(table_name)
        logger.info(f"Columns: {columns}")
        if config_columns:
            for column in config_columns:
                if column in columns:
                    real_get_columns.append(column)
        if len(real_get_columns) == 0:
            log_task_error(
                task_uid,
                f"Task with UID {task_uid} Table {table_name} has no valid columns.",
            )
            return
        table_dir = os.path.join(base_dir, table_name)
        os.makedirs(table_dir, exist_ok=True)
        page_size = 10000
        page = 1
        records_count = collection_task.records_count or 0
        file_index = 1
        rows_buffer = []
        while True:
            rows = connector.query_table_hive(
                table_name,
                real_get_columns,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            if not rows:
                break
            rows_buffer.extend(rows)
            if len(rows_buffer) >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                pd.DataFrame(rows_buffer).to_parquet(file_path, index=False)
                records_count += len(rows_buffer)
                collection_task.records_count = records_count
                log_task_info(
                    task_uid,
                    f"Task with UID {task_uid} get data count {records_count}...",
                )
                rows_buffer = []
                file_index += 1
            page += 1
        if rows_buffer:
            file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
            pd.DataFrame(rows_buffer).to_parquet(file_path, index=False)
            records_count += len(rows_buffer)
            collection_task.records_count = records_count
            log_task_info(
                task_uid,
                f"Task with UID {task_uid} get data count {records_count}...",
            )
        log_task_info(
            task_uid,
            f"Task with UID {task_uid} get data count {collection_task.records_count}...",
        )
    except Exception as e:
        traceback.print_exc()
        log_task_error(
            task_uid,
            f"Task with UID {task_uid} Error occurred while getting table dataset: {e}",
        )


def hive_get_table_dataset_by_sql(
    connector,
    task_uid: str,
    run_sql: str,
    collection_task,
    base_dir: str,
    max_line: int = 10000,
):
    try:
        table_dir = os.path.join(base_dir, "run_sql")
        os.makedirs(table_dir, exist_ok=True)
        rows = connector.execute_custom_query_hive(run_sql)
        if not rows:
            log_task_error(
                task_uid,
                f"Task with UID {task_uid} No results returned from SQL query.",
            )
            return
        file_index = 1
        current_file_row_count = 0
        rows_list = []
        for row in rows:
            if current_file_row_count >= max_line:
                file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
                pd.DataFrame(rows_list[:max_line]).to_parquet(file_path, index=False)
                file_index += 1
                current_file_row_count = 0
                rows_list = []
            rows_list.append(row)
            current_file_row_count += 1
            current_file_row_count += 1
            if current_file_row_count % 10000 == 0:
                collection_task.records_count = current_file_row_count
                log_task_info(
                    task_uid,
                    f"Task with UID {task_uid} get data count {current_file_row_count}...",
                )
        if len(rows_list) > 0:
            file_path = os.path.join(table_dir, f"data_{file_index:04d}.parquet")
            pd.DataFrame(rows_list).to_parquet(file_path, index=False)
        collection_task.total_count = len(rows)
        collection_task.records_count = len(rows)
        log_task_info(
            task_uid,
            f"Task with UID {task_uid} get data count {collection_task.records_count}...",
        )
    except Exception as e:
        log_task_error(
            task_uid,
            f"Task with UID {task_uid} Error occurred while getting table dataset: {e}",
        )
