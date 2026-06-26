import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import mammoth
import pandas as pd
from markdownify import markdownify as md
from pptx import Presentation

from data_server.pod.pod_logger import log_task_error, log_task_info


def convert_excel_to_csv(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith((".xlsx", ".xls")):
        log_task_info(task_uid, f"Source file address：{file_path}")
        try:
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            sheet_count = len(sheet_names)
            
            log_task_info(task_uid, f"Found {sheet_count} sheet(s) in Excel file")
            
            result_files = []
            base_name = os.path.splitext(file_path)[0]
            
            for idx, sheet_name in enumerate(sheet_names, 1):
                try:
                    log_task_info(task_uid, f"Processing sheet {idx}/{sheet_count}: '{sheet_name}'")
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    safe_sheet_name = re.sub(r'[<>:"/\\|?*]', '_', sheet_name)
                    if sheet_count == 1:
                        new_file = f"{base_name}.csv"
                    else:
                        new_file = f"{base_name}_{safe_sheet_name}.csv"
                    
                    # Use utf-8-sig encoding to ensure Excel can open the CSV correctly
                    df.to_csv(new_file, index=False, encoding='utf-8-sig')
                    result_files.append(new_file)
                    log_task_info(task_uid, f"Sheet '{sheet_name}' converted to {new_file}")
                except Exception as sheet_error:
                    log_task_error(task_uid, f"Failed to convert sheet '{sheet_name}': {sheet_error}")
                    continue
            
            os.remove(file_path)
            
            if len(result_files) == 0:
                return {"from": file_path, "to": None, "status": "failure", "error": "No sheets converted"}
            
            return {
                "from": file_path,
                "to": result_files[0] if len(result_files) == 1 else result_files,
                "to_files": result_files,
                "status": "success",
                "sheets_count": len(result_files)
            }
        except Exception as e:
            log_task_error(task_uid, f"convert file {file_path} error: {e}")
            return {"from": file_path, "to": None, "status": "failure", "error": str(e)}
    return None


def convert_excel_to_json(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith((".xlsx", ".xls")):
        log_task_info(task_uid, f"Source file address：{file_path}")
        try:
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            sheet_count = len(sheet_names)
            
            log_task_info(task_uid, f"Found {sheet_count} sheet(s) in Excel file")
            
            result_files = []
            base_name = os.path.splitext(file_path)[0]
            
            for idx, sheet_name in enumerate(sheet_names, 1):
                try:
                    log_task_info(task_uid, f"Processing sheet {idx}/{sheet_count}: '{sheet_name}'")
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    safe_sheet_name = re.sub(r'[<>:"/\\|?*]', '_', sheet_name)
                    if sheet_count == 1:
                        new_file = f"{base_name}.json"
                    else:
                        new_file = f"{base_name}_{safe_sheet_name}.json"
                    
                    df.to_json(new_file, orient="records", force_ascii=False)
                    result_files.append(new_file)
                    log_task_info(task_uid, f"Sheet '{sheet_name}' converted to {new_file}")
                except Exception as sheet_error:
                    log_task_error(task_uid, f"Failed to convert sheet '{sheet_name}': {sheet_error}")
                    continue
            
            os.remove(file_path)
            
            if len(result_files) == 0:
                return {"from": file_path, "to": None, "status": "failure", "error": "No sheets converted"}
            
            return {
                "from": file_path,
                "to": result_files[0] if len(result_files) == 1 else result_files,
                "to_files": result_files,
                "status": "success",
                "sheets_count": len(result_files)
            }
        except Exception as e:
            log_task_error(task_uid, f"convert file {file_path} error: {e}")
            return {"from": file_path, "to": None, "status": "failure", "error": str(e)}
    return None


def convert_excel_to_parquet(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith((".xlsx", ".xls")):
        log_task_info(task_uid, f"Source file address：{file_path}")
        try:
            # Read Excel file to get all sheet names
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            sheet_count = len(sheet_names)
            
            log_task_info(task_uid, f"Found {sheet_count} sheet(s) in Excel file")
            
            result_files = []
            base_name = os.path.splitext(file_path)[0]
            
            # Process each sheet
            for idx, sheet_name in enumerate(sheet_names, 1):
                try:
                    log_task_info(task_uid, f"Processing sheet {idx}/{sheet_count}: '{sheet_name}'")
                    
                    # Read the sheet
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # Data type processing (same as original logic)
                    for col in df.columns:
                        if df[col].dtype == "object":
                            df[col] = df[col].astype(str)
                            df[col] = df[col].replace("nan", None)
                        elif pd.api.types.is_integer_dtype(df[col]):
                            if df[col].isna().any():
                                df[col] = df[col].astype(str)
                        elif pd.api.types.is_float_dtype(df[col]):
                            if df[col].isna().any():
                                pass
                    
                    # Generate output file name
                    # Clean sheet name to remove invalid file system characters
                    safe_sheet_name = re.sub(r'[<>:"/\\|?*]', '_', sheet_name)
                    
                    # If only one sheet, use simple naming; otherwise include sheet name
                    if sheet_count == 1:
                        new_file = f"{base_name}.parquet"
                    else:
                        new_file = f"{base_name}_{safe_sheet_name}.parquet"
                    
                    # Save to parquet
                    df.to_parquet(new_file, index=False, engine="pyarrow")
                    result_files.append(new_file)
                    
                    log_task_info(
                        task_uid, 
                        f"Sheet '{sheet_name}' converted successfully: {new_file} "
                        f"({len(df)} rows, {len(df.columns)} columns)"
                    )
                    
                except Exception as sheet_error:
                    log_task_error(task_uid, f"Failed to convert sheet '{sheet_name}': {sheet_error}")
                    # Continue processing other sheets even if one fails
                    continue
            
            # Clean up source file
            os.remove(file_path)
            
            # Return result
            if len(result_files) == 0:
                return {
                    "from": file_path,
                    "to": None,
                    "status": "failure",
                    "error": "No sheets were successfully converted",
                    "sheets_count": 0
                }
            
            log_task_info(
                task_uid, 
                f"Excel conversion completed: {len(result_files)}/{sheet_count} sheets converted successfully"
            )
            
            # Return format compatible with both single and multiple files
            return {
                "from": file_path,
                "to": result_files[0] if len(result_files) == 1 else result_files,
                "to_files": result_files,  # Always provide list for consistency
                "status": "success",
                "sheets_count": len(result_files)
            }
            
        except Exception as e:
            log_task_error(task_uid, f"convert file {file_path} error: {e}")
            return {
                "from": file_path,
                "to": None,
                "status": "failure",
                "error": str(e)
            }
    return None


def fix_email_links_in_html(html_content: str) -> str:
    pattern1 = r'<a href="(http://[^@]+@[^"]+?)&quot;\s*\\o\s*&quot;(http://[^"]+?)">([^<]+)</a>'

    def replace_email_link1(match):
        url1 = match.group(1)
        url2 = match.group(2)
        link_text = match.group(3)
        if url1 != url2:
            return f'<a href="{url1}">{link_text}</a> <a href="{url2}">{link_text}</a>'
        return f'<a href="{url2}">{link_text}</a>'

    pattern2 = r'<a href="(mailto:[^@]+@[^"]+?)&quot;\s*\\o\s*&quot;mailto:([^"]+?)">([^<]+)</a>'

    def replace_email_link2(match):
        address1 = match.group(1)
        address2_full = f'mailto:{match.group(2)}'
        link_text = match.group(3)
        if address1 != address2_full:
            return f'<a href="{address1}">{link_text}</a> <a href="{address2_full}">{link_text}</a>'
        return f'<a href="{address1}">{link_text}</a>'

    pattern3 = r'<a href="http://@([^"]+?)&quot;\s*\\o\s*&quot;http://([^"]+?)">([^<]+)</a>'

    def replace_email_link3(match):
        address1 = f'http://@{match.group(1)}'
        address2 = f'http://{match.group(2)}'
        link_text = match.group(3)
        if address1 != address2:
            return f'<a href="{address1}">{link_text}</a> <a href="{address2}">{link_text}</a>'
        return f'<a href="{address2}">{link_text}</a>'

    pattern4 = r'<a href="http://([^@]+@[^/"]+?)">([^<]+)</a>'

    def replace_email_link4(match):
        email = match.group(1)
        link_text = match.group(2)
        return f'<a href="http://{email}">{link_text}</a>'

    fixed_html = re.sub(pattern1, replace_email_link1, html_content)
    fixed_html = re.sub(pattern2, replace_email_link2, fixed_html)
    fixed_html = re.sub(pattern3, replace_email_link3, fixed_html)
    fixed_html = re.sub(pattern4, replace_email_link4, fixed_html)
    return fixed_html


def convert_word_to_markdown(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith((".docx", ".doc")):
        log_task_info(task_uid, f"Source file address：{file_path}")
        try:
            with open(file_path, "rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html_content = result.value
            html_content = fix_email_links_in_html(html_content)
            markdown_content = md(html_content)
            markdown_file_path = os.path.splitext(file_path)[0] + ".md"
            with open(markdown_file_path, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_content)
            log_task_info(task_uid, f"convert file {markdown_file_path} succeed")
            os.remove(file_path)
            return {"from": file_path, "to": markdown_file_path, "status": "success"}
        except Exception as e:
            log_task_error(task_uid, f"convert file {file_path} error: {e}")
            return {"from": file_path, "to": None, "status": "failure"}
    return None


def _read_text_file_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def convert_txt_to_markdown(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if not file_path.lower().endswith(".txt"):
        return None
    log_task_info(task_uid, f"Source file address：{file_path}")
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        text_content = _read_text_file_bytes(raw)
        markdown_file_path = os.path.splitext(file_path)[0] + ".md"
        with open(markdown_file_path, "w", encoding="utf-8") as md_file:
            md_file.write(text_content)
        log_task_info(task_uid, f"convert file {markdown_file_path} succeed")
        os.remove(file_path)
        return {"from": file_path, "to": markdown_file_path, "status": "success"}
    except Exception as e:
        log_task_error(task_uid, f"convert file {file_path} error: {e}")
        return {"from": file_path, "to": None, "status": "failure"}


def convert_html_to_markdown(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if not file_path.lower().endswith((".html", ".htm")):
        return None
    log_task_info(task_uid, f"Source file address：{file_path}")
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        html_content = _read_text_file_bytes(raw)
        html_content = fix_email_links_in_html(html_content)
        markdown_content = md(html_content)
        markdown_file_path = os.path.splitext(file_path)[0] + ".md"
        with open(markdown_file_path, "w", encoding="utf-8") as md_file:
            md_file.write(markdown_content)
        log_task_info(task_uid, f"convert file {markdown_file_path} succeed")
        os.remove(file_path)
        return {"from": file_path, "to": markdown_file_path, "status": "success"}
    except Exception as e:
        log_task_error(task_uid, f"convert file {file_path} error: {e}")
        return {"from": file_path, "to": None, "status": "failure"}


def convert_ppt_to_markdown(file_path: str, task_uid) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith((".pptx", ".ppt")):
        log_task_info(task_uid, f"Source file address：{file_path}")
        try:
            prs = Presentation(file_path)
            markdown_content = ""
            for i, slide in enumerate(prs.slides):
                markdown_content += f" lantern slide {i + 1}\n\n"
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        text_content = shape.text.strip()
                        if text_content:
                            if len(text_content) < 50 and "\n" not in text_content:
                                markdown_content += f"## {text_content}\n\n"
                            else:
                                markdown_content += f"{text_content}\n\n"
            markdown_file_path = os.path.splitext(file_path)[0] + ".md"
            with open(markdown_file_path, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_content)
            log_task_info(task_uid, f"convert file {markdown_file_path} succeed")
            os.remove(file_path)
            return {"from": file_path, "to": markdown_file_path, "status": "success"}
        except Exception as e:
            log_task_error(task_uid, f"convert file {file_path} error: {e}")
            return {"from": file_path, "to": None, "status": "failure"}
    return None


def convert_pdf_to_markdown(
    file_path: str,
    task_uid,
    mineru_api_url: Optional[str] = None,
    mineru_backend: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    if file_path.lower().endswith(".pdf"):
        log_task_info(task_uid, f"Source file address：{file_path}")
        try:
            from mineru.cli.common import prepare_env
            from mineru.data.data_reader_writer import FileBasedDataWriter
            from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
            from mineru.utils.enum_class import MakeMode

            server_url = mineru_api_url or os.getenv("MINERU_API_URL", "http://111.4.242.20:30000")
            backend = mineru_backend or os.getenv("MINERU_BACKEND", "http-client")
            log_task_info(task_uid, f"Using MinerU API server: {server_url}, backend: {backend}")

            pdf_file_name = Path(file_path).stem
            temp_output_dir = Path(file_path).parent / f"_temp_pdf_convert_{pdf_file_name}"
            temp_output_dir.mkdir(exist_ok=True)

            result_json_path = temp_output_dir / "mineru_result.json"
            repo_root = Path(__file__).resolve().parents[2]
            mineru_worker_script = repo_root / "data_server" / "pod" / "mineru_worker.py"

            cmd = [
                sys.executable,
                str(mineru_worker_script),
                file_path,
                str(temp_output_dir),
                server_url,
                backend,
                str(result_json_path),
            ]
            process = subprocess.Popen(cmd, cwd=str(repo_root))
            process.wait()

            if process.returncode != 0:
                error_msg = "MinerU subprocess failed"
                if result_json_path.exists():
                    try:
                        with open(result_json_path, "r", encoding="utf-8") as f:
                            result_data = json.load(f)
                            if not result_data.get("success", False):
                                error_msg = result_data.get("error", error_msg)
                    except Exception:
                        pass
                log_task_error(task_uid, f"MinerU subprocess failed: {error_msg}")
                raise RuntimeError(f"MinerU subprocess failed: {error_msg}")

            if not result_json_path.exists():
                raise FileNotFoundError(f"Result JSON file not found: {result_json_path}")

            with open(result_json_path, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            if not result_data.get("success", False):
                error_msg = result_data.get("error", "Unknown error")
                log_task_error(task_uid, f"MinerU subprocess error: {error_msg}")
                raise RuntimeError(f"MinerU subprocess error: {error_msg}")

            middle_json = result_data["middle_json"]
            local_image_dir, local_md_dir = prepare_env(str(temp_output_dir), pdf_file_name, "vlm")
            _ = local_image_dir
            md_writer = FileBasedDataWriter(local_md_dir)

            pdf_info = middle_json["pdf_info"]
            image_dir = ""
            md_content_str = vlm_union_make(pdf_info, MakeMode.MM_MD, image_dir)

            markdown_filename = f"{pdf_file_name}.md"
            md_writer.write_string(markdown_filename, md_content_str)

            markdown_file_path = Path(local_md_dir) / markdown_filename
            final_markdown_path = os.path.splitext(file_path)[0] + ".md"
            shutil.move(str(markdown_file_path), final_markdown_path)

            log_task_info(task_uid, f"convert file {final_markdown_path} succeed")
            os.remove(file_path)
            if temp_output_dir.exists():
                shutil.rmtree(temp_output_dir)
            return {"from": file_path, "to": final_markdown_path, "status": "success"}
        except Exception as e:
            log_task_error(task_uid, f"convert file {file_path} error: {e}")
            temp_output_dir = Path(file_path).parent / f"_temp_pdf_convert_{Path(file_path).stem}"
            if temp_output_dir.exists():
                try:
                    shutil.rmtree(temp_output_dir)
                except Exception:
                    pass
            return {"from": file_path, "to": None, "status": "failure"}
    return None


def search_files(folder_path: str, types: List[int]) -> Tuple[bool, List[str]]:
    type_map: Dict[int, List[str]] = {
        0: [".ppt", ".pptx"],
        1: [".doc", ".docx"],
        3: [".xls", ".xlsx"],
        7: [".pdf"],
        8: [".txt"],
        9: [".html", ".htm"],
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
    return bool(len(found_files) > 0), found_files
