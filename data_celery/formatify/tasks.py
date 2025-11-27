import os
import shutil
import time
import traceback
import json
import subprocess
import sys
from typing import List, Dict, Tuple, Optional
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
        try:
            ingesterCSGHUB = load_ingester(
                dataset_path=tmp_path,
                repo_id=format_task.from_csg_hub_repo_id,
                branch=format_task.from_csg_hub_dataset_branch,
                user_name=user_name,
                user_token=user_token,
            )
            ingester_result = ingesterCSGHUB.ingest()
            insert_formatity_task_log_info(format_task.task_uid, f"Download directory completed... Directory address：{ingester_result}")
        except Exception as e:
            error_msg = str(e)
            # 检查是否是认证错误
            if "401" in error_msg or "Unauthorized" in error_msg:
                detailed_error = f"认证失败：无法访问数据集 {format_task.from_csg_hub_repo_id}。可能原因：1) Token 已过期，请重新登录；2) Token 无效；3) 没有访问该数据集的权限。错误详情：{error_msg}"
                insert_formatity_task_log_error(format_task.task_uid, detailed_error)
                logger.error(f"Authentication failed for task {format_task.task_uid}: {error_msg}")
            else:
                insert_formatity_task_log_error(format_task.task_uid, f"Failed to download dataset: {error_msg}")
                logger.error(f"Failed to download dataset for task {format_task.task_uid}: {error_msg}")
            format_task.task_status = DataFormatTaskStatusEnum.ERROR.value
            db_session.commit()
            return
        work_dir = Path(tmp_path).joinpath('work')
        file_bool = search_files(tmp_path,[format_task.from_data_type])

        if not file_bool:
            insert_formatity_task_log_info(format_task.task_uid, f"file not found. task ended....")
            format_task.task_status = DataFormatTaskStatusEnum.ERROR.value
            db_session.commit()
            return
        insert_formatity_task_log_info(format_task.task_uid, f"Start converting file...")
        
        # 创建新目录，只包含转换成功的文件
        converted_dir = Path(tmp_path).joinpath('converted')
        ensure_directory_exists(str(converted_dir))
        
        # 创建 meta 文件夹
        meta_dir = converted_dir / "meta"
        ensure_directory_exists(str(meta_dir))
        
        # 获取目标文件扩展名列表
        type_map: Dict[int, List[str]] = {
            0: ['.ppt', '.pptx'],  # PPT
            1: ['.doc', '.docx'],  # Word
            3: ['.xls', '.xlsx'],  # Excel
            7: ['.pdf']  # PDF
        }
        target_extensions = set()
        if format_task.from_data_type in type_map:
            for ext in type_map[format_task.from_data_type]:
                target_extensions.add(ext.lower())
        
        # 先统计总文件数（使用与转换时完全相同的逻辑）
        total_count = 0
        base_path = Path(ingester_result)
        file_list_for_count = []
        for root, dirs, files in os.walk(ingester_result):
            for file in files:
                file_path_full = os.path.join(root, file)
                # 只处理指定类型的文件（与转换时的逻辑完全一致）
                file_ext = Path(file_path_full).suffix.lower()
                if file_ext in target_extensions:
                    total_count += 1
                    file_list_for_count.append(file_path_full)
        
        insert_formatity_task_log_info(format_task.task_uid, f'Found {total_count} files to convert')
        if total_count > 0:
            insert_formatity_task_log_info(format_task.task_uid, f'Files to convert: {[Path(f).name for f in file_list_for_count[:5]]}{"..." if total_count > 5 else ""}')
        
        # 初始化统计信息
        success_count = 0
        failure_count = 0
        
        # 初始化 meta.json 数据结构（包含正确的总数）
        # 注意：total 在初始化时设置后，后续不再修改，只更新 success 和 failure
        meta_data = {
            "job_id": format_task.id,
            "job_name": format_task.name,
            "source_repo": format_task.from_csg_hub_repo_id,
            "source_branch": format_task.from_csg_hub_dataset_branch,
            "files": [],
            "result": {
                "total": total_count,  # 固定总数，后续不再修改
                "success": 0,
                "failure": 0
            }
        }
        meta_file_path = meta_dir / "meta.json"
        
        # 先上传包含总数的 meta.json 文件
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, indent=2, ensure_ascii=False)
        insert_formatity_task_log_info(format_task.task_uid, f'Generated initial meta.json file with total: {total_count} (total will remain fixed)')
        
        # 创建 exporter（复用同一个实例）
        exporter = load_exporter(
            export_path=str(converted_dir),
            repo_id=format_task.to_csg_hub_repo_id,
            branch=format_task.to_csg_hub_dataset_default_branch,
            user_name=user_name,
            user_token=user_token,
            path_is_dir=True,
            work_dir=str(work_dir)
        )
        
        # 先上传包含总数的 meta.json（重要：必须上传成功，包含总文件数信息）
        # 如果失败3次，任务立即终止
        # 注意：第一次尝试不算在重试次数里，只有失败后才开始重试计数
        initial_upload_success = False
        initial_upload_retry_count = 0
        max_initial_retries = 3  # 初始上传最多重试3次
        
        # 第一次尝试（不算在重试次数里）
        try:
            insert_formatity_task_log_info(format_task.task_uid, f'开始上传初始 meta.json (总文件数: {total_count})')
            exporter.export_large_folder()
            insert_formatity_task_log_info(format_task.task_uid, f'[成功] 初始 meta.json 上传成功 (总文件数: {total_count})')
            initial_upload_success = True
            upload_failure_count = 0  # 重置失败计数
        except Exception as e:
            # 第一次失败，开始重试
            initial_upload_retry_count += 1
            error_msg = f'[上传失败 {initial_upload_retry_count}/{max_initial_retries}] 初始 meta.json 上传失败: {str(e)}'
            insert_formatity_task_log_error(format_task.task_uid, error_msg)
            logger.error(error_msg)
            
            # 重试最多3次
            while not initial_upload_success and initial_upload_retry_count < max_initial_retries:
                try:
                    initial_upload_retry_count += 1
                    insert_formatity_task_log_info(format_task.task_uid, f'[重试 {initial_upload_retry_count}/{max_initial_retries}] 开始上传初始 meta.json (总文件数: {total_count})')
                    exporter.export_large_folder()
                    insert_formatity_task_log_info(format_task.task_uid, f'[成功] 初始 meta.json 上传成功 (总文件数: {total_count})')
                    initial_upload_success = True
                    upload_failure_count = 0  # 重置失败计数
                except Exception as e:
                    error_msg = f'[上传失败 {initial_upload_retry_count}/{max_initial_retries}] 初始 meta.json 上传失败: {str(e)}'
                    insert_formatity_task_log_error(format_task.task_uid, error_msg)
                    logger.error(error_msg)
                    
                    if initial_upload_retry_count >= max_initial_retries:
                        # 初始上传失败3次，任务立即终止
                        final_error_msg = f'[任务终止] 初始 meta.json 上传失败 {max_initial_retries} 次，任务已停止。总文件数: {total_count}'
                        insert_formatity_task_log_error(format_task.task_uid, final_error_msg)
                        logger.error(final_error_msg)
                        format_task.task_status = DataFormatTaskStatusEnum.ERROR.value
                        db_session.commit()
                        raise RuntimeError(f'初始 meta.json 上传失败 {max_initial_retries} 次，任务已终止。总文件数: {total_count}')
        
        # 如果初始上传失败，不应该继续执行
        if not initial_upload_success:
            error_msg = f'[任务终止] 初始 meta.json 上传失败，任务已停止。总文件数: {total_count}'
            insert_formatity_task_log_error(format_task.task_uid, error_msg)
            logger.error(error_msg)
            format_task.task_status = DataFormatTaskStatusEnum.ERROR.value
            db_session.commit()
            raise RuntimeError(f'初始 meta.json 上传失败，任务已终止。总文件数: {total_count}')
        
        # 选择转换函数
        convert_func = None
        match format_task.from_data_type:
            case DataFormatTypeEnum.Excel.value:
                match format_task.to_data_type:
                    case DataFormatTypeEnum.Csv.value:
                        convert_func = convert_excel_to_csv
                    case DataFormatTypeEnum.Json.value:
                        convert_func = convert_excel_to_json
                    case DataFormatTypeEnum.Parquet.value:
                        convert_func = convert_excel_to_parquet
            case DataFormatTypeEnum.Word.value:
                match format_task.to_data_type:
                    case DataFormatTypeEnum.Markdown.value:
                        convert_func = convert_word_to_markdown
            case DataFormatTypeEnum.PPT.value:
                match format_task.to_data_type:
                    case DataFormatTypeEnum.Markdown.value:
                        convert_func = convert_ppt_to_markdown
            case DataFormatTypeEnum.PDF.value:
                match format_task.to_data_type:
                    case DataFormatTypeEnum.Markdown.value:
                        convert_func = convert_pdf_to_markdown
        
        if convert_func is None:
            insert_formatity_task_log_error(format_task.task_uid, f"Unsupported conversion: {getFormatTypeName(format_task.from_data_type)} -> {getFormatTypeName(format_task.to_data_type)}")
            format_task.task_status = DataFormatTaskStatusEnum.ERROR.value
            db_session.commit()
            return
        
        insert_formatity_task_log_info(format_task.task_uid,
                                       f"Change the table of contents：{ingester_result}，Source file type：{getFormatTypeName(format_task.from_data_type)}，Target file type：{getFormatTypeName(format_task.to_data_type)}")
        
        # 用于跟踪已使用的文件名，处理重名情况
        used_names = {}
        
        # 遍历文件并实时转换、上传
        upload_failure_count = 0  # 连续上传失败计数（初始上传失败已计入）
        max_upload_failures = 3  # 最大连续上传失败次数
        
        for root, dirs, files in os.walk(ingester_result):
            # 检查任务是否被停止
            db_session.refresh(format_task)
            if format_task.task_status == DataFormatTaskStatusEnum.STOP.value:
                insert_formatity_task_log_info(format_task.task_uid, "Task stopped by user")
                return
            
            for file in files:
                # 检查任务是否被停止
                db_session.refresh(format_task)
                if format_task.task_status == DataFormatTaskStatusEnum.STOP.value:
                    insert_formatity_task_log_info(format_task.task_uid, "Task stopped by user")
                    return
                
                file_path_full = os.path.join(root, file)
                
                # 只处理指定类型的文件
                file_ext = Path(file_path_full).suffix.lower()
                if file_ext not in target_extensions:
                    continue
                
                # 执行转换
                # 对于 PDF 转 MD，需要传递 mineru_api_url 参数
                if format_task.from_data_type == DataFormatTypeEnum.PDF.value and format_task.to_data_type == DataFormatTypeEnum.Markdown.value:
                    result = convert_func(file_path_full, format_task.task_uid, format_task.mineru_api_url)
                else:
                    result = convert_func(file_path_full, format_task.task_uid)
                
                if not isinstance(result, dict):
                    continue
                
                from_file = result['from']
                to_file = result['to']
                status = result['status']
                
                # 计算原文件的相对路径（相对于 base_path），用于 meta.json
                try:
                    from_rel_path = str(Path(from_file).relative_to(base_path))
                except ValueError:
                    from_rel_path = Path(from_file).name
                
                # 确保 from 路径使用正斜杠（跨平台兼容）
                from_rel_path = from_rel_path.replace('\\', '/')
                
                if status == 'success' and to_file and Path(to_file).exists():
                    src_path = Path(to_file)
                    # 直接使用文件名，如果重名则添加序号
                    file_name = src_path.name
                    if file_name in used_names:
                        # 文件名冲突，添加序号
                        name_part = src_path.stem
                        ext_part = src_path.suffix
                        counter = used_names[file_name]
                        new_name = f"{name_part}_{counter}{ext_part}"
                        used_names[file_name] += 1
                        used_names[new_name] = 1
                        dst_path = converted_dir / new_name
                        final_to_file = new_name
                        insert_formatity_task_log_info(format_task.task_uid, f'Copied converted file (renamed due to conflict): {file_name} -> {new_name}')
                    else:
                        dst_path = converted_dir / file_name
                        used_names[file_name] = 1
                        final_to_file = file_name
                        insert_formatity_task_log_info(format_task.task_uid, f'Copied converted file: {file_name}')
                    
                    # 复制文件到 converted 目录
                    shutil.copy2(src_path, dst_path)
                    
                    # to 路径：相对于 converted_dir 的路径
                    to_rel_path = final_to_file.replace('\\', '/')
                    
                    # 立即上传转换成功的文件（上传成功后才更新统计信息）
                    try:
                        exporter.export_large_folder()
                        insert_formatity_task_log_info(format_task.task_uid, f'Uploaded converted file: {final_to_file}')
                        
                        # 文件上传成功后才更新统计信息
                        success_count += 1
                        meta_data["files"].append({
                            "from": from_rel_path,
                            "to": to_rel_path,
                            "status": "success"
                        })
                        meta_data["result"]["success"] = success_count
                        upload_failure_count = 0  # 重置失败计数
                    except Exception as e:
                        upload_failure_count += 1
                        error_msg = f'[上传失败 {upload_failure_count}/{max_upload_failures}] 文件上传失败: {final_to_file}, 错误: {str(e)}'
                        insert_formatity_task_log_error(format_task.task_uid, error_msg)
                        logger.error(error_msg)
                        
                        # 文件上传失败，立即更新统计信息为失败并更新 meta.json
                        failure_count += 1
                        meta_data["files"].append({
                            "from": from_rel_path,
                            "to": to_rel_path,
                            "status": "failure",
                            "error": f"上传失败: {str(e)}"
                        })
                        meta_data["result"]["failure"] = failure_count
                        
                        # 确保 total 保持不变（不应该被修改）
                        assert meta_data["result"]["total"] == total_count, f"Total should remain {total_count}, but got {meta_data['result']['total']}"
                        
                        # 立即更新并上传 meta.json（记录上传失败的文件）
                        with open(meta_file_path, 'w', encoding='utf-8') as f:
                            json.dump(meta_data, f, indent=2, ensure_ascii=False)
                        try:
                            exporter.export_large_folder()
                            insert_formatity_task_log_info(format_task.task_uid, f'Updated meta.json with upload failure record (total: {total_count}, success: {success_count}, failure: {failure_count})')
                            # 注意：meta.json 上传成功不重置 upload_failure_count，只有文件上传成功才重置
                        except Exception as e:
                            # meta.json 更新上传失败只记录日志，不抛出异常，不影响文件上传失败计数
                            error_msg = f'meta.json 更新上传失败 (文件: {final_to_file}), 错误: {str(e)}'
                            insert_formatity_task_log_error(format_task.task_uid, error_msg)
                            logger.error(error_msg)
                            # 不增加 upload_failure_count，不影响文件上传失败计数
                        
                        # 如果连续上传失败次数过多，停止任务
                        if upload_failure_count >= max_upload_failures:
                            error_msg = f'[任务终止] 连续上传失败 {upload_failure_count} 次，任务已停止。'
                            insert_formatity_task_log_error(format_task.task_uid, error_msg)
                            logger.error(error_msg)
                            format_task.task_status = DataFormatTaskStatusEnum.ERROR.value
                            db_session.commit()
                            raise RuntimeError(f'连续上传失败 {upload_failure_count} 次，任务已停止')
                    
                    # 确保 total 保持不变（不应该被修改）
                    assert meta_data["result"]["total"] == total_count, f"Total should remain {total_count}, but got {meta_data['result']['total']}"
                    
                    # 文件上传成功时，更新并上传 meta.json
                    if upload_failure_count == 0:  # 只有上传成功时才更新（失败时已经在上面更新了）
                        with open(meta_file_path, 'w', encoding='utf-8') as f:
                            json.dump(meta_data, f, indent=2, ensure_ascii=False)
                        try:
                            exporter.export_large_folder()
                            insert_formatity_task_log_info(format_task.task_uid, f'Updated and uploaded meta.json (total: {total_count}, success: {success_count}, failure: {failure_count})')
                            # 注意：meta.json 上传成功不重置 upload_failure_count，只有文件上传成功才重置
                        except Exception as e:
                            # meta.json 更新上传失败只记录日志，不抛出异常，不影响文件上传失败计数
                            error_msg = f'meta.json 更新上传失败 (文件: {final_to_file}), 错误: {str(e)}'
                            insert_formatity_task_log_error(format_task.task_uid, error_msg)
                            logger.error(error_msg)
                            # 不增加 upload_failure_count，不影响文件上传失败计数
                else:
                    # 转换失败的文件也记录到 meta.json
                    failure_count += 1
                    meta_entry = {
                        "from": from_rel_path,
                        "to": None,
                        "status": "failure"
                    }
                    # 如果有错误信息，也记录到 meta.json
                    if "error" in result:
                        meta_entry["error"] = result["error"]
                    meta_data["files"].append(meta_entry)
                    meta_data["result"]["failure"] = failure_count
                    # 确保 total 保持不变（不应该被修改）
                    assert meta_data["result"]["total"] == total_count, f"Total should remain {total_count}, but got {meta_data['result']['total']}"
                    
                    # 更新并上传 meta.json（包含失败记录，不抛出异常，只记录日志）
                    with open(meta_file_path, 'w', encoding='utf-8') as f:
                        json.dump(meta_data, f, indent=2, ensure_ascii=False)
                    try:
                        exporter.export_large_folder()
                        insert_formatity_task_log_info(format_task.task_uid, f'Updated meta.json with failure record (total: {total_count}, success: {success_count}, failure: {failure_count})')
                        # 注意：meta.json 上传成功不重置 upload_failure_count，只有文件上传成功才重置
                    except Exception as e:
                        # meta.json 更新上传失败只记录日志，不抛出异常，不影响文件上传失败计数
                        error_msg = f'meta.json 更新上传失败 (转换失败的文件), 错误: {str(e)}'
                        insert_formatity_task_log_error(format_task.task_uid, error_msg)
                        logger.error(error_msg)
                        # 不增加 upload_failure_count，不影响文件上传失败计数
        
        insert_formatity_task_log_info(format_task.task_uid, f'All files processed. Total: {total_count}, Success: {success_count}, Failure: {failure_count}')
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
        task_uid: str,
        mineru_api_url: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    执行格式转换任务
    返回转换结果列表，每个结果包含 from, to, status
    """
    insert_formatity_task_log_info(task_uid,
                                   f"Change the table of contents：{tmp_path}，Source file type：{getFormatTypeName(from_type)}，Target file type：{getFormatTypeName(to_type)}")
    conversion_results = []
    match from_type:
        case DataFormatTypeEnum.Excel.value:
            match to_type:
                case DataFormatTypeEnum.Csv.value:
                    conversion_results = traverse_files(tmp_path, convert_excel_to_csv, task_uid)
                case DataFormatTypeEnum.Json.value:
                    conversion_results = traverse_files(tmp_path, convert_excel_to_json, task_uid)
                case DataFormatTypeEnum.Parquet.value:
                    conversion_results = traverse_files(tmp_path, convert_excel_to_parquet, task_uid)
        case DataFormatTypeEnum.Word.value:
            match to_type:
                case DataFormatTypeEnum.Markdown.value:
                    conversion_results = traverse_files(tmp_path, convert_word_to_markdown, task_uid)
        case DataFormatTypeEnum.PPT.value:
            match to_type:
                case DataFormatTypeEnum.Markdown.value:
                    conversion_results = traverse_files(tmp_path, convert_ppt_to_markdown, task_uid)
        case DataFormatTypeEnum.PDF.value:
            match to_type:
                case DataFormatTypeEnum.Markdown.value:
                    # 对于 PDF 转 MD，需要传递 mineru_api_url
                    conversion_results = traverse_files(tmp_path, convert_pdf_to_markdown, task_uid, mineru_api_url)
    return conversion_results


def traverse_files(file_path: str, func, task_uid, mineru_api_url: Optional[str] = None) -> List[Dict[str, str]]:
    """
    遍历文件并执行转换函数
    返回转换结果列表，每个结果包含 from, to, status
    """
    conversion_results = []
    for root, dirs, files in os.walk(file_path):
        for file in files:
            file_path_full = os.path.join(root, file)
            # 对于 PDF 转 MD，传递 mineru_api_url 参数
            if func == convert_pdf_to_markdown and mineru_api_url is not None:
                result = func(file_path_full, task_uid, mineru_api_url)
            else:
                result = func(file_path_full, task_uid)
            # result 应该是字典，包含 from, to, status
            if isinstance(result, dict):
                conversion_results.append(result)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            sub_results = traverse_files(dir_path, func, task_uid, mineru_api_url)
            conversion_results.extend(sub_results)
    return conversion_results


def convert_excel_to_csv(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith(('.xlsx', '.xls')):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            df = pd.read_excel(file_path)
            new_file = os.path.splitext(file_path)[0] + '.csv'
            df.to_csv(new_file, index=False)
            insert_formatity_task_log_info(task_uid, f'convert file {new_file} succeed')
            os.remove(file_path)
            return {
                "from": file_path,
                "to": new_file,
                "status": "success"
            }
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return {
                "from": file_path,
                "to": None,
                "status": "failure"
            }
    else:
        return None  # 非目标文件，返回 None


def convert_excel_to_json(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith(('.xlsx', '.xls')):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            df = pd.read_excel(file_path)
            new_file = os.path.splitext(file_path)[0] + '.json'
            df.to_json(new_file, orient='records', force_ascii=False)
            insert_formatity_task_log_info(task_uid, f'convert file {new_file} succeed')
            os.remove(file_path)
            return {
                "from": file_path,
                "to": new_file,
                "status": "success"
            }
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return {
                "from": file_path,
                "to": None,
                "status": "failure"
            }
    else:
        return None  # 非目标文件，返回 None


def convert_excel_to_parquet(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith(('.xlsx', '.xls')):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            # 读取 Excel 文件
            df = pd.read_excel(file_path)
            
            # 处理混合类型列，避免 Parquet 类型转换错误
            for col in df.columns:
                if df[col].dtype == 'object':
                    # 对于 object 类型（通常是混合类型），统一转换为字符串
                    # 这样可以避免 Parquet 的类型转换错误
                    df[col] = df[col].astype(str)
                    # 将 'nan' 字符串转换为 None
                    df[col] = df[col].replace('nan', None)
                elif pd.api.types.is_integer_dtype(df[col]):
                    # 整数类型，检查是否有 NaN，如果有则转换为字符串
                    if df[col].isna().any():
                        df[col] = df[col].astype(str)
                elif pd.api.types.is_float_dtype(df[col]):
                    # 浮点数类型，检查是否有 NaN
                    if df[col].isna().any():
                        # NaN 值在 Parquet 中是可以处理的，但为了安全，可以保持原样
                        pass
            
            new_file = os.path.splitext(file_path)[0] + '.parquet'
            # 使用 pyarrow 引擎
            df.to_parquet(new_file, index=False, engine='pyarrow')
            insert_formatity_task_log_info(task_uid, f'convert file {new_file} succeed')
            os.remove(file_path)
            return {
                "from": file_path,
                "to": new_file,
                "status": "success"
            }
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return {
                "from": file_path,
                "to": None,
                "status": "failure"
            }
    else:
        return None  # 非目标文件，返回 None


def convert_word_to_markdown(file_path: str, task_uid) -> Optional[Dict[str, str]]:
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
            return {
                "from": file_path,
                "to": markdown_file_path,
                "status": "success"
            }
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return {
                "from": file_path,
                "to": None,
                "status": "failure"
            }
    else:
        return None  # 非目标文件，返回 None


def convert_ppt_to_markdown(file_path: str, task_uid) -> Optional[Dict[str, str]]:
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
            return {
                "from": file_path,
                "to": markdown_file_path,
                "status": "success"
            }
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            return {
                "from": file_path,
                "to": None,
                "status": "failure"
            }
    else:
        return None  # 非目标文件，返回 None


def convert_pdf_to_markdown(file_path: str, task_uid, mineru_api_url: Optional[str] = None) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith('.pdf'):
        insert_formatity_task_log_info(task_uid, f'Source file address：{file_path}')
        try:
            from mineru.cli.common import prepare_env
            from mineru.data.data_reader_writer import FileBasedDataWriter
            from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
            from mineru.utils.enum_class import MakeMode
            
            # 优先级：传入的参数 > 环境变量 > 默认值
            if mineru_api_url:
                server_url = mineru_api_url
            else:
                server_url = os.getenv("MINERU_API_URL", "http://111.4.242.20:30000")
            backend = "http-client"
            
            # 记录使用的 MinerU API 地址，便于调试
            insert_formatity_task_log_info(task_uid, f'Using MinerU API server: {server_url}')
            
            pdf_file_name = Path(file_path).stem
            temp_output_dir = Path(file_path).parent / f"_temp_pdf_convert_{pdf_file_name}"
            temp_output_dir.mkdir(exist_ok=True)
            
            # 在独立进程中运行 MinerU（使用 subprocess）
            result_json_path = temp_output_dir / "mineru_result.json"
            script_dir = Path(__file__).parent
            mineru_worker_script = script_dir / "mineru_worker.py"
            
            python_exe = sys.executable
            cmd = [
                python_exe,
                str(mineru_worker_script),
                file_path,
                str(temp_output_dir),
                server_url,
                backend,
                str(result_json_path)
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=str(Path(__file__).parent.parent.parent)
            )
            
            process.wait()
            
            if process.returncode != 0:
                error_msg = "MinerU subprocess failed"
                if result_json_path.exists():
                    try:
                        with open(result_json_path, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                            if not result_data.get("success", False):
                                error_msg = result_data.get("error", error_msg)
                    except:
                        pass
                insert_formatity_task_log_error(task_uid, f'MinerU subprocess failed: {error_msg}')
                raise RuntimeError(f"MinerU subprocess failed: {error_msg}")
            
            if not result_json_path.exists():
                raise FileNotFoundError(f"Result JSON file not found: {result_json_path}")
            
            with open(result_json_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            
            if not result_data.get("success", False):
                error_msg = result_data.get("error", "Unknown error")
                insert_formatity_task_log_error(task_uid, f'MinerU subprocess error: {error_msg}')
                raise RuntimeError(f"MinerU subprocess error: {error_msg}")
            
            middle_json = result_data["middle_json"]
            
            # 生成 Markdown 内容
            local_image_dir, local_md_dir = prepare_env(str(temp_output_dir), pdf_file_name, "vlm")
            md_writer = FileBasedDataWriter(local_md_dir)
            
            pdf_info = middle_json["pdf_info"]
            image_dir = ""
            md_content_str = vlm_union_make(pdf_info, MakeMode.MM_MD, image_dir)
            
            markdown_filename = f"{pdf_file_name}.md"
            md_writer.write_string(markdown_filename, md_content_str)
            
            markdown_file_path = Path(local_md_dir) / markdown_filename
            final_markdown_path = os.path.splitext(file_path)[0] + '.md'
            shutil.move(str(markdown_file_path), final_markdown_path)
            
            insert_formatity_task_log_info(task_uid, f'convert file {final_markdown_path} succeed')
            os.remove(file_path)
            
            if temp_output_dir.exists():
                shutil.rmtree(temp_output_dir)
            
            return {
                "from": file_path,
                "to": final_markdown_path,
                "status": "success"
            }
        except Exception as e:
            print(f"convert file {file_path} error: {e}")
            insert_formatity_task_log_error(task_uid, f"convert file {file_path} error: {e}")
            
            temp_output_dir = Path(file_path).parent / f"_temp_pdf_convert_{Path(file_path).stem}"
            if temp_output_dir.exists():
                try:
                    shutil.rmtree(temp_output_dir)
                except:
                    pass
            
            return {
                "from": file_path,
                "to": None,
                "status": "failure"
            }
    else:
        return None  # 非目标文件，返回 None


def search_files(folder_path: str, types: List[int]) -> Tuple[bool, List[str]]:

    type_map: Dict[int, List[str]] = {
        0: ['.ppt', '.pptx'],  # PPT
        1: ['.doc', '.docx'],  # Word
        3: ['.xls', '.xlsx'],  # Excel
        7: ['.pdf']  # PDF
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