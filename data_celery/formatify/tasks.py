import os
import shutil
import time
import traceback
from data_celery.main import celery_app
from sqlalchemy.orm import Session
from loguru import logger
from pathlib import Path

from data_celery.utils import get_format_folder_path, ensure_directory_exists, ensure_directory_exists_remove
from data_celery.db import FormatifyManager
from data_engine.exporter.load import load_exporter
from data_server.formatify.FormatifyModels import DataFormatTask, DataFormatTaskStatusEnum, DataFormatTypeEnum, \
    getFormatTypeName
from data_server.database.session import get_sync_session
from data_engine.ingester.load import load_ingester
import pandas as pd
import mammoth
from markdownify import markdownify as md
from pptx import Presentation
from data_celery.mongo_tools.tools import insert_formatity_task_log_info, insert_formatity_task_log_error
from pycsghub.upload_large_folder.main import upload_large_folder_internal
from pycsghub.cmd.repo_types import RepoType
from pycsghub.utils import (build_csg_headers,
                            model_id_to_group_owner_name,
                            get_endpoint,
                            REPO_TYPE_DATASET)
from data_engine.utils.env import GetHubEndpoint
@celery_app.task
def format_task(task_id: int, user_name: str, user_token: str):

    tmp_path: str = None
    db_session: Session = None
    format_task: DataFormatTask = None

    try:
        db_session: Session = get_sync_session()
        format_task: DataFormatTask = FormatifyManager.get_formatify_task(db_session, task_id)
        tmp_path = get_format_folder_path(format_task.task_uid)
        insert_formatity_task_log_info(format_task.task_uid, f"Create temporary directory：{tmp_path}")
        ensure_directory_exists(tmp_path)

        insert_formatity_task_log_info(format_task.task_uid, f"Start downloading directory....")
        ingesterCSGHUB = load_ingester(
            dataset_path=tmp_path,
            repo_id=format_task.from_csg_hub_repo_id,
            branch=format_task.from_csg_hub_dataset_branch,
            user_name=user_name,
            user_token=user_token,
        )
        ingester_result = ingesterCSGHUB.ingest()
        insert_formatity_task_log_info(format_task.task_uid, f"Download directory completed... Directory address：{ingester_result}")
        work_dir = Path(tmp_path).joinpath('work')
        file_bool = search_files(tmp_path,[format_task.from_data_type])

        if not file_bool:
            insert_formatity_task_log_info(format_task.task_uid, f"file not found. task ended....")
            format_task.task_status = DataFormatTaskStatusEnum.ERROR.value
            db_session.commit()
            return
        insert_formatity_task_log_info(format_task.task_uid, f"Start converting file...")

        format_task_func(
            tmp_path=ingester_result,
            from_type=format_task.from_data_type,
            to_type=format_task.to_data_type,
            task_uid=format_task.task_uid,
        )
        insert_formatity_task_log_info(format_task.task_uid, f"Conversion file complete....")
        insert_formatity_task_log_info(format_task.task_uid, f"Start uploading directory...")

        exporter = load_exporter(
            export_path=ingester_result,
            repo_id=format_task.to_csg_hub_repo_id,
            branch=format_task.to_csg_hub_dataset_default_branch,
            user_name=user_name,
            user_token=user_token,
            path_is_dir=True,
            work_dir=str(work_dir)
        )
        exporter.export_large_folder()
        insert_formatity_task_log_info(format_task.task_uid, 'Upload completed...')
        format_task.task_status = DataFormatTaskStatusEnum.COMPLETED.value
        db_session.commit()
        pass
    except Exception as e:
        traceback.print_exc()
        format_task.task_status = DataFormatTaskStatusEnum.ERROR.value
        db_session.commit()
        insert_formatity_task_log_error(format_task.task_uid, f"Conversion task failed: {str(e)}")
    finally:
        pass

        if tmp_path:
            shutil.rmtree(tmp_path)
            insert_formatity_task_log_info(format_task.task_uid, f"Delete temporary directory：{tmp_path}")


def format_task_func(
        tmp_path: str,
        from_type: int,
        to_type: int,
        task_uid: str
):
    insert_formatity_task_log_info(task_uid,
                                   f"Change the table of contents：{tmp_path}，Source file type：{getFormatTypeName(from_type)}，Source file type：{getFormatTypeName(to_type)}")
    match from_type:
        case DataFormatTypeEnum.Excel.value:
            match to_type:
                case DataFormatTypeEnum.Csv.value:
                    traverse_files(tmp_path, convert_excel_to_csv, task_uid)
                case DataFormatTypeEnum.Json.value:
                    traverse_files(tmp_path, convert_excel_to_json, task_uid)
                case DataFormatTypeEnum.Parquet.value:
                    traverse_files(tmp_path, convert_excel_to_parquet, task_uid)
        case DataFormatTypeEnum.Word.value:
            match to_type:
                case DataFormatTypeEnum.Markdown.value:
                    traverse_files(tmp_path, convert_word_to_markdown, task_uid)
        case DataFormatTypeEnum.PPT.value:
            match to_type:
                case DataFormatTypeEnum.Markdown.value:
                    traverse_files(tmp_path, convert_ppt_to_markdown, task_uid)


def traverse_files(file_path: str, func, task_uid):
    for root, dirs, files in os.walk(file_path):
        for file in files:
            file_path = os.path.join(root, file)
            func(file_path, task_uid)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            traverse_files(dir_path, func, task_uid)


def convert_excel_to_csv(file_path: str, task_uid):
    if file_path.lower().endswith(('.xlsx', '.xls')):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            df = pd.read_excel(file_path)
            new_file = os.path.splitext(file_path)[0] + '.csv'
            df.to_csv(new_file, index=False)
            insert_formatity_task_log_info(task_uid, f'convert file {new_file} succeed')
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return False
    else:
        return True


def convert_excel_to_json(file_path: str, task_uid):
    if file_path.lower().endswith(('.xlsx', '.xls')):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            df = pd.read_excel(file_path)
            new_file = os.path.splitext(file_path)[0] + '.json'
            df.to_json(new_file, orient='records', force_ascii=False)
            insert_formatity_task_log_info(task_uid, f'convert file {new_file} succeed')
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")

            return False
    else:

        return True


def convert_excel_to_parquet(file_path: str, task_uid):
    if file_path.lower().endswith(('.xlsx', '.xls')):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            df = pd.read_excel(file_path)
            new_file = os.path.splitext(file_path)[0] + '.parquet'
            df.to_parquet(new_file + '.parquet', index=False)
            insert_formatity_task_log_info(task_uid, f'convert file {new_file} succeed')
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return False
    else:
        return True


def convert_word_to_markdown(file_path: str, task_uid):
    if file_path.lower().endswith(('.docx', '.doc')):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            with open(file_path, "rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html_content = result.value
            markdown_content = md(html_content)
            markdown_file_path = os.path.splitext(file_path)[0] + '.md'
            with open(markdown_file_path, 'w', encoding='utf-8') as md_file:
                md_file.write(markdown_content)
            insert_formatity_task_log_info(task_uid, f'convert file {markdown_file_path} succeed')
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return False
    else:

        return True


def convert_ppt_to_markdown(file_path: str, task_uid):
    if file_path.lower().endswith(('.pptx', '.ppt')):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            prs = Presentation(file_path)
            markdown_content = ""
            for i, slide in enumerate(prs.slides):
                markdown_content += f" lantern slide {i + 1}\n\n"
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        text_content = shape.text.strip()
                        if text_content:
                            if len(text_content) < 50 and '\n' not in text_content:
                                markdown_content += f"## {text_content}\n\n"
                            else:
                                markdown_content += f"{text_content}\n\n"
            markdown_file_path = os.path.splitext(file_path)[0] + '.md'
            with open(markdown_file_path, 'w', encoding='utf-8') as md_file:
                md_file.write(markdown_content)
            insert_formatity_task_log_info(task_uid, f'convert file {markdown_file_path} succeed')
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return False
    else:

        return True


from typing import List, Dict, Tuple

def search_files(folder_path: str, types: List[int]) -> Tuple[bool, List[str]]:

    type_map: Dict[int, List[str]] = {
        0: ['.ppt', '.pptx'],  # PPT
        1: ['.doc', '.docx'],  # Word
        3: ['.xls', '.xlsx']  # Excel
    }


    target_extensions = set()
    for file_type in types:
        if file_type in type_map:
            for ext in type_map[file_type]:
                target_extensions.add(ext.lower())


    found_files: List[str] = []

    def traverse(current_path: str) -> None:

        try:

            entries = os.listdir(current_path)

            for entry in entries:
                entry_path = os.path.join(current_path, entry)

                if os.path.isdir(entry_path):

                    traverse(entry_path)
                elif os.path.isfile(entry_path):

                    file_ext = os.path.splitext(entry)[1].lower()
                    if file_ext in target_extensions:
                        found_files.append(entry_path)

        except PermissionError:
            print(f"No permission to access the folder: {current_path}")
        except Exception as e:
            print(f"Processing path {current_path} error: {str(e)}")


    traverse(folder_path)


    return bool(len(found_files) > 0)