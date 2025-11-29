from pathlib import Path
import os
import json
import hashlib
import re
from loguru import logger

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from data_engine.format import load_formatter
from data_engine.ops.base_op import OPERATORS
from data_engine.utils.file_utils import find_files_with_suffix
from data_engine.utils.model_utils import get_opencsg_model_path

# Import for new upload method
from pycsghub.upload_large_folder.main import upload_large_folder_internal
from pycsghub.cmd.repo_types import RepoType
from pycsghub.utils import get_endpoint
from data_engine.utils.env import GetHubEndpoint
import traceback


TOOL_NAME = 'md_to_jsonl_preprocess_internal'


def sanitize_filename(filename: str, max_length: int = 40) -> str:
    """
    Convert filename to safe ASCII-only format for cross-platform compatibility.
    
    Rules:
    1. Keep ASCII letters and digits (a-z, A-Z, 0-9)
    2. Replace non-ASCII characters and special symbols with underscore
    3. Merge consecutive underscores into single one
    4. Add 8-char hash suffix based on original filename for uniqueness
    5. If no ASCII chars remain, use 'file_' prefix with 16-char hash
    
    Examples:
        '传神csghub.md' -> 'csghub_a1b2c3d4'
        '测试文件123.md' -> '123_5e6f7g8h'
        'example.md' -> 'example'
        '我的文档.md' -> 'file_9a8b7c6d5e4f3a2b'
    
    :param filename: Original filename (with or without extension)
    :param max_length: Maximum length for ASCII part (default 40)
    :return: Safe ASCII filename without extension
    """
    # Remove extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Keep only ASCII letters, digits; replace others with underscore
    ascii_part = re.sub(r'[^a-zA-Z0-9]+', '_', name_without_ext)
    
    # Remove leading/trailing underscores
    ascii_part = ascii_part.strip('_')
    
    # Generate hash based on original filename for uniqueness
    hash_obj = hashlib.md5(name_without_ext.encode('utf-8'))
    hash_full = hash_obj.hexdigest()
    
    # Case 1: No ASCII characters remain, use 'file_' + 16-char hash
    if not ascii_part:
        return f"file_{hash_full[:16]}"
    
    # Case 2: Only ASCII characters and no special chars in original, use as-is
    if ascii_part == name_without_ext:
        return ascii_part[:max_length]
    
    # Case 3: Mixed content, keep ASCII part + 8-char hash suffix
    ascii_part_truncated = ascii_part[:max_length]
    hash_suffix = hash_full[:8]
    return f"{ascii_part_truncated}_{hash_suffix}"


@TOOLS.register_module(TOOL_NAME)
class MdToJsonlPreprocess(TOOL):
    """
    Convert MD files to JSONL format with token-based chunking.
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param tool_defination: tool definition
        :param params: executed parameters
        """
        super().__init__(tool_defination, params)
        
        # Override exporter to use custom upload method that supports Chinese filenames
        self._original_exporter = self.exporter
        self.exporter = self._create_custom_exporter()
        
        # Get parameters from tool definition
        model_name = next(
            (item.value for item in self.tool_def.params if item.name == "hf_tokenizer"),
            "EleutherAI/pythia-6.9b-deduped")  # Default tokenizer
        
        # Download model from OpenCSG Hub
        try:
            logger.info(f'Downloading model from OpenCSG Hub: {model_name}')
            self.model_path = get_opencsg_model_path(model_name)
            logger.info(f'Model download completed, path: {self.model_path}')
        except Exception as e:
            logger.error(f'Failed to download model from OpenCSG Hub: {str(e)}')
            raise RuntimeError(f'Unable to download model {model_name}: {str(e)}')
        
        # Save original model name for logging
        self.hf_tokenizer = model_name
        
        # Convert chunk_size to int, as it may come as string from params
        chunk_size_value = next(
            (item.value for item in self.tool_def.params if item.name == "chunk_size"),
            512)
        try:
            self.chunk_size = int(chunk_size_value) if chunk_size_value is not None else 512
        except (ValueError, TypeError):
            self.chunk_size = 512
        
        # Convert overlap to int, as it may come as string from params
        overlap_value = next(
            (item.value for item in self.tool_def.params if item.name == "overlap"),
            0)
        try:
            self.overlap = int(overlap_value) if overlap_value is not None else 0
            # Ensure overlap is less than chunk_size
            if self.overlap >= self.chunk_size:
                self.overlap = 0
        except (ValueError, TypeError):
            self.overlap = 0
        
        # Get chunk_method parameter (default: "token")
        self.chunk_method = next(
            (item.value for item in self.tool_def.params if item.name == "chunk_method"),
            "token")
        
        # Get min_sentences_per_chunk parameter (only used for sentence chunking)
        # Only read this parameter if using sentence-based chunking
        if self.chunk_method == "sentence":
            min_sentences_value = next(
                (item.value for item in self.tool_def.params if item.name == "min_sentences_per_chunk"),
                1)
            try:
                self.min_sentences_per_chunk = int(min_sentences_value) if min_sentences_value is not None else 1
            except (ValueError, TypeError):
                self.min_sentences_per_chunk = 1
        else:
            self.min_sentences_per_chunk = 1  # Not used for token-based chunking
        
        # text_key is fixed as 'text' since MD files are converted to this format before passing to tool
        self.text_key = "text"
    
    def _create_custom_exporter(self):
        """
        Create a custom exporter that uses upload_large_folder_internal
        instead of Repository.upload() to properly handle Chinese filenames.
        
        :return: Custom exporter object with export_from_files method
        """
        class CustomExporter:
            def __init__(self, parent):
                self.parent = parent
            
            def export_from_files(self, upload_path: Path):
                """
                Export method using upload_large_folder_internal for Chinese filename support.
                
                :param upload_path: path with files to upload
                :return: branch name
                """
                # 🔍 诊断日志: 检查上传路径
                logger.info(f'='*80)
                logger.info(f'[EXPORT DEBUG] Starting export_from_files()')
                logger.info(f'[EXPORT DEBUG] Upload path type: {type(upload_path)}, value: {upload_path}')
                logger.info(f'[EXPORT DEBUG] Upload path (str): {str(upload_path)}')
                logger.info(f'[EXPORT DEBUG] Upload path exists: {os.path.exists(upload_path)}')
                
                if not os.path.exists(upload_path):
                    logger.error(f'[EXPORT DEBUG] Upload path does not exist!')
                    return None
                    
                # 🔍 诊断日志: 列出所有要上传的文件
                try:
                    files_to_upload = os.listdir(upload_path)
                    logger.info(f'[EXPORT DEBUG] Files in upload directory: {len(files_to_upload)} files')
                    for i, filename in enumerate(files_to_upload, 1):
                        file_path = os.path.join(upload_path, filename)
                        file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                        # 显示文件名的不同编码形式
                        logger.info(f'[EXPORT DEBUG]   File {i}: {filename}')
                        logger.info(f'[EXPORT DEBUG]     - repr(): {repr(filename)}')
                        logger.info(f'[EXPORT DEBUG]     - bytes: {filename.encode("utf-8")}')
                        logger.info(f'[EXPORT DEBUG]     - size: {file_size} bytes')
                        logger.info(f'[EXPORT DEBUG]     - is_file: {os.path.isfile(file_path)}')
                except Exception as e:
                    logger.error(f'[EXPORT DEBUG] Error listing files: {str(e)}')
                    traceback.print_exc()
                
                if len(os.listdir(upload_path)) == 0:
                    logger.info(f'[EXPORT DEBUG] The target dir is empty, no need to upload anything, abort.')
                    return None
                
                if self.parent.tool_def.repo_id is None or len(self.parent.tool_def.repo_id) == 0:
                    logger.info('[EXPORT DEBUG] No repo_id specified, skip upload.')
                    return 'N/A'
                
                # 🔍 诊断日志: repo信息
                logger.info(f'[EXPORT DEBUG] Target repo_id: {self.parent.tool_def.repo_id}')
                logger.info(f'[EXPORT DEBUG] User token (first 10 chars): {self.parent.executed_params.user_token[:10] if self.parent.executed_params.user_token else "None"}...')
                
                try:
                    # Get branch name
                    branch = self.parent.tool_def.branch if self.parent.tool_def.branch and len(self.parent.tool_def.branch) > 0 else 'main'
                    logger.info(f'[EXPORT DEBUG] Original branch: {branch}')
                    
                    output_branch_name = self.parent._get_available_branch(branch)
                    logger.info(f'[EXPORT DEBUG] Output branch name: {output_branch_name}')
                    
                    # 🔍 诊断日志: 上传参数
                    endpoint = get_endpoint(endpoint=GetHubEndpoint())
                    logger.info(f'[EXPORT DEBUG] Upload parameters:')
                    logger.info(f'[EXPORT DEBUG]   - repo_id: {self.parent.tool_def.repo_id}')
                    logger.info(f'[EXPORT DEBUG]   - local_path: {str(upload_path)}')
                    logger.info(f'[EXPORT DEBUG]   - repo_type: {RepoType.DATASET}')
                    logger.info(f'[EXPORT DEBUG]   - revision: {output_branch_name}')
                    logger.info(f'[EXPORT DEBUG]   - endpoint: {endpoint}')
                    logger.info(f'[EXPORT DEBUG]   - num_workers: 1')
                    
                    logger.info(f'='*80)
                    logger.info(f'Start to upload {upload_path} to repo: {self.parent.tool_def.repo_id} with branch: {output_branch_name}')
                    logger.info(f'Using upload_large_folder_internal for Chinese filename support')
                    logger.info(f'='*80)
                    
                    # Use upload_large_folder_internal for better Unicode/Chinese filename handling
                    upload_large_folder_internal(
                        repo_id=self.parent.tool_def.repo_id,
                        local_path=str(upload_path),
                        repo_type=RepoType.DATASET,
                        revision=output_branch_name,
                        endpoint=endpoint,
                        token=self.parent.executed_params.user_token,
                        num_workers=1,
                        print_report=False,
                        print_report_every=1,
                        allow_patterns=None,
                        ignore_patterns=None
                    )
                    
                    logger.info(f'='*80)
                    logger.info(f'[EXPORT DEBUG] Upload completed successfully!')
                    logger.info(f'[EXPORT DEBUG] Uploaded to repo: {self.parent.tool_def.repo_id}')
                    logger.info(f'[EXPORT DEBUG] Branch: {output_branch_name}')
                    logger.info(f'='*80)
                    logger.info(f'Successfully uploaded to repo: {self.parent.tool_def.repo_id} with branch: {output_branch_name}')
                    return output_branch_name
                    
                except Exception as e:
                    logger.error(f'='*80)
                    logger.error(f'[EXPORT DEBUG] Upload failed with exception!')
                    logger.error(f'[EXPORT DEBUG] Exception type: {type(e).__name__}')
                    logger.error(f'[EXPORT DEBUG] Exception message: {str(e)}')
                    logger.error(f'[EXPORT DEBUG] Exception args: {e.args}')
                    logger.error(f'[EXPORT DEBUG] Full traceback:')
                    traceback.print_exc()
                    logger.error(f'='*80)
                    logger.error(f'Failed to upload folder to {self.parent.tool_def.repo_id}: {str(e)}')
                    raise
        
        return CustomExporter(self)

    def process(self):
        """
        Process MD files and convert to JSONL format with chunking support.
        Supports both token-based and sentence-based chunking methods.
        Each MD file will be processed separately and saved as a separate JSONL file.
        """
        logger.info(f'Scanning for MD files in {self.tool_def.dataset_path}')
        
        # Scan for all MD files in the dataset path
        file_dict = find_files_with_suffix(self.tool_def.dataset_path, ['.md'])
        md_files = file_dict.get('.md', [])
        
        if not md_files:
            logger.warning(f'No MD files found in {self.tool_def.dataset_path}')
            # Fallback to original behavior: try to load as-is (might be jsonl/json files)
            logger.info('Falling back to original loading method...')
            
            # Ensure the export directory exists
            if not os.path.exists(self.tool_def.export_path):
                os.makedirs(self.tool_def.export_path, exist_ok=True)
            
            # Create meta directory for meta.json
            meta_dir = Path(self.tool_def.export_path) / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            meta_file_path = meta_dir / "meta.json"
            
            # Try to extract job_name from work_dir path
            job_name = self.tool_def.name
            work_dir_path = Path(self.executed_params.work_dir)
            if work_dir_path.name and '_' in work_dir_path.name:
                parts = work_dir_path.name.split('_')
                if len(parts) >= 2:
                    potential_job_name = '_'.join(parts[:-1])
                    if potential_job_name:
                        job_name = potential_job_name
            
            formatter = load_formatter(
                dataset_path=self.tool_def.dataset_path,
                text_keys=['text'],
                suffixes=['.md', '.jsonl', '.json']
            )
            dataset = formatter.load_dataset(num_proc=self.tool_def.np)
            
            # Create mapper operator (using downloaded model path)
            if self.chunk_method == "sentence":
                mapper_op = OPERATORS.modules['md_to_jsonl_sentence_chunk_mapper'](
                    hf_tokenizer=self.model_path,
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.overlap,
                    min_sentences_per_chunk=self.min_sentences_per_chunk,
                )
            else:
                mapper_op = OPERATORS.modules['md_to_jsonl_chunk_mapper'](
                    hf_tokenizer=self.model_path,
                    chunk_size=self.chunk_size,
                    overlap=self.overlap,
                )
            
            dataset = mapper_op.run(dataset=dataset, exporter=None, tracer=None)
            num_chunks = len(dataset)
            
            # Save to default x.jsonl
            output_file = os.path.join(self.tool_def.export_path, 'x.jsonl')
            dataset.to_json(output_file, force_ascii=False, num_proc=self.tool_def.np)
            logger.info(f'Dataset saved to {output_file} ({num_chunks} chunks)')
            
            # Generate meta.json for fallback case
            # Keep original dataset_path (including Chinese chars if any)
            dataset_path_for_meta = self.tool_def.dataset_path or "unknown"
            if dataset_path_for_meta != "unknown":
                dataset_path_for_meta = os.path.basename(dataset_path_for_meta)
            
            meta_data = {
                "job_name": job_name,
                "tool_name": TOOL_NAME,
                "source_repo": self.tool_def.repo_id or "",
                "source_branch": self.tool_def.branch or "main",
                "target_repo": self.tool_def.repo_id or "",
                "files": [
                    {
                        "from": dataset_path_for_meta,
                        "to": "x.jsonl",
                        "status": "success",
                        "chunks": num_chunks
                    }
                ],
                "result": {
                    "total": 1,
                    "success": 1,
                    "failure": 0
                },
                "parameters": {
                    "chunk_method": self.chunk_method,
                    "chunk_size": self.chunk_size,
                    "overlap": self.overlap,
                    "hf_tokenizer": self.hf_tokenizer,
                    "min_sentences_per_chunk": self.min_sentences_per_chunk
                },
                "statistics": {
                    "total_chunks": num_chunks,
                    "avg_chunks_per_file": float(num_chunks)
                },
                "note": "Fallback mode: processed as single dataset (no MD files found)"
            }
            
            with open(meta_file_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2, ensure_ascii=False)
            logger.info(f'Generated meta.json for fallback mode (total_chunks: {num_chunks})')
            
            return Path(self.tool_def.export_path)
        
        logger.info(f'Found {len(md_files)} MD file(s) to process')
        
        # Ensure the export directory exists
        if not os.path.exists(self.tool_def.export_path):
            os.makedirs(self.tool_def.export_path, exist_ok=True)
        
        # Create meta directory for meta.json
        meta_dir = Path(self.tool_def.export_path) / "meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_file_path = meta_dir / "meta.json"
        
        # Initialize meta.json data structure
        total_count = len(md_files)
        base_path = Path(self.tool_def.dataset_path)
        
        # Try to extract job_name from work_dir path (format: job_name_uuid)
        job_name = self.tool_def.name  # Use tool name as default
        work_dir_path = Path(self.executed_params.work_dir)
        if work_dir_path.name and '_' in work_dir_path.name:
            # Try to extract job_name from path like "job_name_uuid"
            parts = work_dir_path.name.split('_')
            if len(parts) >= 2:
                # Assume last part is uuid, rest is job_name
                potential_job_name = '_'.join(parts[:-1])
                if potential_job_name:
                    job_name = potential_job_name
        
        meta_data = {
            "job_name": job_name,
            "tool_name": TOOL_NAME,
            "source_repo": self.tool_def.repo_id or "",
            "source_branch": self.tool_def.branch or "main",
            "target_repo": self.tool_def.repo_id or "",
            "files": [],
            "result": {
                "total": total_count,
                "success": 0,
                "failure": 0
            },
            "parameters": {
                "chunk_method": self.chunk_method,
                "chunk_size": self.chunk_size,
                "overlap": self.overlap,
                "hf_tokenizer": self.hf_tokenizer,
                "min_sentences_per_chunk": self.min_sentences_per_chunk
            },
            "statistics": {
                "total_chunks": 0,
                "avg_chunks_per_file": 0.0
            }
        }
        
        # Save initial meta.json
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, indent=2, ensure_ascii=False)
        logger.info(f'Generated initial meta.json file with total: {total_count} files')
        
        # Create mapper operator (can be reused for all files, using downloaded model path)
        if self.chunk_method == "sentence":
            # Use sentence-based chunking (supports mixed Chinese-English by default)
            mapper_op = OPERATORS.modules['md_to_jsonl_sentence_chunk_mapper'](
                hf_tokenizer=self.model_path,
                chunk_size=self.chunk_size,
                chunk_overlap=self.overlap,
                min_sentences_per_chunk=self.min_sentences_per_chunk,
            )
            logger.info(f'Using sentence-based chunking (mixed Chinese-English) with chunk_size={self.chunk_size}, '
                       f'chunk_overlap={self.overlap}, min_sentences_per_chunk={self.min_sentences_per_chunk}')
        else:
            # Use token-based chunking (default)
            mapper_op = OPERATORS.modules['md_to_jsonl_chunk_mapper'](
                hf_tokenizer=self.model_path,
                chunk_size=self.chunk_size,
                overlap=self.overlap,
            )
            logger.info(f'Using token-based chunking with chunk_size={self.chunk_size}, overlap={self.overlap}')
        
        # Process each MD file separately
        processed_files = []
        failed_files = []
        total_chunks = 0
        
        # Track all generated output filenames to avoid conflicts
        # This handles cases like: test.md, test1.md, folder/test.md
        # Should output: test.jsonl, test1.jsonl, test2.jsonl (not test1.jsonl again!)
        generated_outputs = set()  # Set of all generated output base names (without .jsonl)
        
        for md_file_path in md_files:
            # Ensure md_file_path is str (not bytes) for cross-platform compatibility
            if isinstance(md_file_path, bytes):
                md_file_path = md_file_path.decode('utf-8', errors='replace')
            
            # Calculate relative path for meta.json (original path with potential non-ASCII chars)
            try:
                original_rel_path = str(Path(md_file_path).relative_to(base_path))
            except ValueError:
                # If relative path calculation fails, use filename
                original_rel_path = os.path.basename(md_file_path)
            
            # Ensure path uses forward slashes (cross-platform compatibility)
            original_rel_path = original_rel_path.replace('\\', '/')
            
            try:
                logger.info(f'Processing file: {md_file_path}')
                
                # Load dataset for this single file
                # Handle encoding for both Windows and Linux
                try:
                    # Ensure path is properly encoded for the OS
                    if os.name == 'nt':  # Windows
                        # Windows handles Unicode paths natively in Python 3
                        file_path_to_load = md_file_path
                    else:  # Linux/Unix
                        # Ensure UTF-8 encoding
                        if isinstance(md_file_path, str):
                            file_path_to_load = md_file_path
                        else:
                            file_path_to_load = md_file_path.decode('utf-8', errors='replace')
                    
                    formatter = load_formatter(
                        dataset_path=file_path_to_load,
                        text_keys=['text'],
                        suffixes=['.md']
                    )
                    dataset = formatter.load_dataset(num_proc=self.tool_def.np)
                except (UnicodeDecodeError, UnicodeEncodeError) as e:
                    raise RuntimeError(f'Failed to load file due to encoding issue: {md_file_path}. '
                                     f'Error: {str(e)}') from e
                
                logger.info(f'Loaded {len(dataset)} sample(s) from {os.path.basename(md_file_path)}')
                
                # Apply mapper to split text
                dataset = mapper_op.run(dataset=dataset, exporter=None, tracer=None)
                
                num_chunks = len(dataset)
                logger.info(f'After chunking, {os.path.basename(md_file_path)} has {num_chunks} chunk(s)')
                
                # Generate output filename - preserve original filename (including Chinese chars)
                # All files output to same directory, use numeric suffix for duplicates
                md_filename = os.path.basename(md_file_path)
                base_name = os.path.splitext(md_filename)[0]
                
                # Handle duplicate filenames by adding numeric suffix
                # Check against all generated outputs to avoid conflicts (e.g., test.md + test1.md + folder/test.md)
                output_base_name = base_name
                suffix = 0
                
                # Keep incrementing suffix until we find an unused filename
                while output_base_name in generated_outputs:
                    suffix += 1
                    output_base_name = f"{base_name}{suffix}"
                
                # Mark this output name as used
                generated_outputs.add(output_base_name)
                
                output_filename = output_base_name + '.jsonl'
                output_file = os.path.join(self.tool_def.export_path, output_filename)
                
                # Log if filename has numeric suffix due to duplication
                if suffix > 0:
                    logger.info(f'Duplicate filename detected: "{base_name}" -> "{output_base_name}" (added suffix {suffix})')
                
                # Save dataset to JSONL file with UTF-8 encoding (cross-platform compatible)
                try:
                    dataset.to_json(output_file, force_ascii=False, num_proc=self.tool_def.np)
                except Exception as e:
                    raise RuntimeError(f'Failed to save JSONL file: {output_file}. Error: {str(e)}') from e
                
                processed_files.append(output_file)
                total_chunks += num_chunks
                
                # Record success in meta.json
                to_rel_path = output_filename.replace('\\', '/')
                file_record = {
                    "from": original_rel_path,  # Keep original relative path with Chinese chars
                    "to": to_rel_path,           # Output filename with Chinese chars preserved
                    "status": "success",
                    "chunks": num_chunks
                }
                
                # Add note if numeric suffix was added due to duplicate filename
                if suffix > 0:
                    file_record["note"] = f"Duplicate filename, added suffix {suffix}"
                
                meta_data["files"].append(file_record)
                meta_data["result"]["success"] += 1
                
                # Update meta.json immediately with UTF-8 encoding
                with open(meta_file_path, 'w', encoding='utf-8') as f:
                    json.dump(meta_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f'Successfully saved {os.path.basename(md_file_path)} -> {output_filename} ({num_chunks} chunks)')
                
            except Exception as e:
                error_msg = f'Failed to process {md_file_path}: {str(e)}'
                logger.error(error_msg)
                failed_files.append((md_file_path, str(e)))
                
                # Record failure in meta.json
                failure_record = {
                    "from": original_rel_path,  # Keep original path with Chinese chars
                    "to": None,
                    "status": "failure",
                    "error": str(e)
                }
                
                meta_data["files"].append(failure_record)
                meta_data["result"]["failure"] += 1
                
                # Update meta.json immediately with UTF-8 encoding
                with open(meta_file_path, 'w', encoding='utf-8') as f:
                    json.dump(meta_data, f, indent=2, ensure_ascii=False)
                
                # Continue processing other files even if one fails
        
        # Calculate final statistics
        success_count = meta_data["result"]["success"]
        failure_count = meta_data["result"]["failure"]
        avg_chunks = total_chunks / success_count if success_count > 0 else 0.0
        
        meta_data["statistics"]["total_chunks"] = total_chunks
        meta_data["statistics"]["avg_chunks_per_file"] = round(avg_chunks, 2)
        
        # Ensure total remains correct
        assert meta_data["result"]["total"] == total_count, \
            f"Total should remain {total_count}, but got {meta_data['result']['total']}"
        
        # Save final meta.json with statistics
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, indent=2, ensure_ascii=False)
        logger.info(f'Updated final meta.json (total: {total_count}, success: {success_count}, failure: {failure_count}, total_chunks: {total_chunks})')
        
        # Summary
        logger.info(f'Processing completed. Successfully processed {len(processed_files)} file(s)')
        if failed_files:
            logger.warning(f'Failed to process {len(failed_files)} file(s):')
            for failed_file, error in failed_files:
                logger.warning(f'  - {failed_file}: {error}')
        
        if not processed_files:
            raise RuntimeError('No files were successfully processed')
        
        # Return the export directory (already contains _data from base_tool.__init__)
        return Path(self.tool_def.export_path)

    def _get_available_branch(self, origin_branch: str) -> str:
        """
        Get available branch name (auto-increment version number).
        Same logic as csghub_exporter.get_avai_branch()
        
        :param origin_branch: original branch name
        :return: available branch name
        """
        import requests
        from pycsghub.utils import build_csg_headers
        
        action_endpoint = get_endpoint(endpoint=GetHubEndpoint())
        url = f"{action_endpoint}/api/v1/datasets/{self.tool_def.repo_id}/branches"
        headers = build_csg_headers(
            token=self.executed_params.user_token,
            headers={"Content-Type": "application/json"}
        )
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            if response.status_code != 200:
                logger.warning(f"Cannot request repo {self.tool_def.repo_id} branches, using origin branch: {origin_branch}")
                return origin_branch
            
            jsonRes = response.json()
            if jsonRes.get("msg") != "OK":
                logger.warning(f"Cannot read repo {self.tool_def.repo_id} branches, using origin branch: {origin_branch}")
                return origin_branch
            
            branches = jsonRes.get("data", [])
            valid_branches = [b['name'] for b in branches]
            valid_branches.sort()
            
            logger.info(f'repo {self.tool_def.repo_id} all branches: {valid_branches}')
            
            # Auto-increment version number (v1, v2, v3, ...)
            latest_num = 0
            for b in valid_branches:
                if origin_branch == "main" and re.match(r"^v\d+$", b):
                    num_str = b[1:]  # Remove 'v' prefix
                    if num_str.isdigit():
                        latest_num = max(latest_num, int(num_str))
                elif b.startswith(origin_branch) and len(b) > len(origin_branch):
                    num_str = b[len(origin_branch) + 1:]
                    if num_str.isdigit():
                        latest_num = max(latest_num, int(num_str))
            
            if origin_branch == "main":
                return f"v{latest_num + 1}" if latest_num > 0 else "v1"
            else:
                if latest_num > 0:
                    return f"{origin_branch}.{latest_num + 1}"
                else:
                    # Check if origin_branch exists
                    if origin_branch in valid_branches:
                        return f"{origin_branch}.1"
                    else:
                        return origin_branch
                        
        except Exception as e:
            logger.warning(f"Error getting branches: {str(e)}, using origin branch: {origin_branch}")
            return origin_branch

    @classmethod
    @property
    def description(cls):
        return "Convert MD files to JSONL format with chunking support."

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("chunk_method", DataType.STRING, {
                "token": "token",
                "sentence": "sentence"
            }, "token"),
            Param("hf_tokenizer", DataType.SEARCH_SELECT, {
                "EleutherAI/pythia-6.9b-deduped": "EleutherAI/pythia-6.9b-deduped",
                "hfl/chinese-bert-wwm-ext": "hfl/chinese-bert-wwm-ext"
            }, "EleutherAI/pythia-6.9b-deduped"),
            Param("chunk_size", DataType.PositiveFloat, None, 512),
            Param("overlap", DataType.PositiveFloat, None, 0),
            Param("min_sentences_per_chunk", DataType.PositiveFloat, None, 1),
        ]

