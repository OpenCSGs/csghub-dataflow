from fastapi import APIRouter, Query
import requests
import os
import subprocess
import tempfile
import shutil
from loguru import logger
from ...schemas.responses import response_success, response_fail
from data_engine.utils.cache_utils import DATA_JUICER_MODELS_CACHE
from typing import Optional

router = APIRouter()


@router.get("/check-model", summary="检查模型是否可用于md_to_jsonl_preprocess工具")
def check_model_for_md_to_jsonl(
    model_name: str = Query(..., description="模型名称，例如：EleutherAI/pythia-6.9b-deduped")
):
    """
    Check if the specified model can be used in md_to_jsonl_preprocess tool.
    
    This endpoint will:
    1. Query model information from OpenCSG Hub API
    2. Check if the model exists and has http_clone_url
    3. If the model is already downloaded, check if it contains tokenizer files
    4. If the model is not downloaded, use shallow clone to quickly check if it contains tokenizer files
    5. Return the model name if available, None if not available
    
    :param model_name: Model name
    :return: Response containing model name (str) if available, None if not available
    """
    try:
        # Query model from OpenCSG Hub API
        csghub_endpoint = os.getenv('CSGHUB_ENDPOINT', 'https://hub.opencsg.com')
        api_url = f'{csghub_endpoint}/api/v1/models'
        params = {
            'page': 1,
            'per': 1,
            'search': model_name,
            'sort': 'trending',
            'source': ''
        }
        logger.info(f'Checking model with api_url: {api_url}')
        logger.info(f'Checking model availability: {model_name}')
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check if model is found
        if not data.get('data') or len(data['data']) == 0:
            logger.warning(f'Model not found in OpenCSG Hub: {model_name}')
            return response_success(
                data=None,
                msg='模型未在OpenCSG Hub中找到'
            )
        
        # Get the first matching model information
        model_info = data['data'][0]
        model_name_from_api = model_info.get('path', model_name)  # Get path field from API response
        repository = model_info.get('repository', {})
        http_clone_url = repository.get('http_clone_url')
        
        # Check if http_clone_url exists
        if not http_clone_url:
            logger.warning(f'Model {model_name} has no http_clone_url')
            return response_success(
                data=None,
                msg='模型缺少http_clone_url，无法下载'
            )
        
        # Check if model is already in local cache
        model_cache_path = os.path.join(DATA_JUICER_MODELS_CACHE, model_name.replace('/', '_'))
        if os.path.exists(model_cache_path) and os.path.isdir(model_cache_path):
            # Check if it's a valid git repository
            git_dir = os.path.join(model_cache_path, '.git')
            if os.path.exists(git_dir):
                # Check if tokenizer files exist
                # md_to_jsonl_preprocess tool only needs tokenizer files, not model weights
                files_in_dir = [f for f in os.listdir(model_cache_path) 
                              if f != '.git' and not f.startswith('.')]
                tokenizer_files = [f for f in files_in_dir 
                                 if any(keyword in f.lower() for keyword in 
                                       ['tokenizer', 'vocab', 'config.json', 'merges', 'special_tokens'])]
                
                if not tokenizer_files:
                    logger.warning(f'Model {model_name} exists locally but has no tokenizer files')
                    return response_success(
                        data=None,
                        msg='模型已下载但缺少tokenizer文件，无法用'
                    )
                else:
                    # ✅ Additional check: verify files are not empty
                    non_empty_files = []
                    for f in tokenizer_files:
                        file_path = os.path.join(model_cache_path, f)
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            if file_size > 0:
                                non_empty_files.append(f'{f} ({file_size} bytes)')
                    
                    if not non_empty_files:
                        logger.warning(f'Model {model_name} exists locally but all tokenizer files are empty')
                        logger.warning(f'Empty files: {tokenizer_files[:5]}')
                        return response_success(
                            data=None,
                            msg='模型已下载但tokenizer文件内容为空，无法使用'
                        )
                    
                    logger.info(f'Model {model_name} exists locally with valid tokenizer files: {non_empty_files[:3]}')
                    return response_success(
                        data=model_name_from_api,
                        msg='模型已下载且包含tokenizer文件，可用'
                    )
        
        # Model not downloaded, use shallow clone to quickly check if it contains tokenizer files
        logger.info(f'Model {model_name} not downloaded, performing shallow clone to check tokenizer files...')
        temp_dir = None
        try:
            # Create temporary directory for shallow clone
            temp_dir = tempfile.mkdtemp(prefix=f'model_check_{model_name.replace("/", "_")}_')
            
            # Set git environment variables
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'
            env['GIT_ASKPASS'] = 'echo'
            env['GIT_LFS_SKIP_SMUDGE'] = '1'  # Skip LFS file download
            
            # Use shallow clone (depth=1) to quickly download
            # ⚠️ Remove --filter=blob:none to ensure we get actual file contents, not just tree structure
            # This matches the actual download behavior in model_utils.py
            logger.info(f'Performing shallow clone to {temp_dir}...')
            clone_result = subprocess.run(
                ['git', 'clone', '--depth', '1', http_clone_url, temp_dir],
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout
                env=env
            )
            
            if clone_result.returncode != 0:
                logger.warning(f'Shallow clone failed: {clone_result.stderr}')
                # Clone failed, cannot verify if model is available
                return response_success(
                    data=None,
                    msg='模型在OpenCSG Hub中存在且有http_clone_url，但浅克隆检查失败，无法验证模型是否可用（可能是网络问题）'
                )
            
            # Check if tokenizer files exist in temporary directory
            if os.path.exists(temp_dir):
                files_in_dir = [f for f in os.listdir(temp_dir) 
                              if f != '.git' and not f.startswith('.')]
                tokenizer_files = [f for f in files_in_dir 
                                 if any(keyword in f.lower() for keyword in 
                                       ['tokenizer', 'vocab', 'config.json', 'merges', 'special_tokens'])]
                
                if not tokenizer_files:
                    logger.warning(f'Model {model_name} cloned but has no tokenizer files')
                    return response_success(
                        data=None,
                        msg='模型仓库中缺少tokenizer文件，无法用'
                    )
                else:
                    # ✅ Additional check: verify files are not empty (not just placeholders)
                    non_empty_files = []
                    for f in tokenizer_files:
                        file_path = os.path.join(temp_dir, f)
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            if file_size > 0:
                                non_empty_files.append(f'{f} ({file_size} bytes)')
                    
                    if not non_empty_files:
                        logger.warning(f'Model {model_name} has tokenizer files but they are all empty')
                        logger.warning(f'Empty files: {tokenizer_files[:5]}')
                        return response_success(
                            data=None,
                            msg='模型tokenizer文件存在但内容为空，仓库可能未正确初始化'
                        )
                    
                    logger.info(f'Model {model_name} contains valid tokenizer files: {non_empty_files[:3]}')
                    return response_success(
                        data=model_name_from_api,
                        msg='模型包含tokenizer文件，可用'
                    )
            else:
                logger.warning(f'Temp directory not created after clone: {temp_dir}')
                return response_success(
                    data=None,
                    msg='模型在OpenCSG Hub中存在且有http_clone_url，但临时目录创建失败，无法验证模型是否可用'
                )
                
        except subprocess.TimeoutExpired:
            logger.warning(f'Shallow clone timeout for model {model_name}')
            return response_success(
                data=None,
                msg='模型在OpenCSG Hub中存在且有http_clone_url，但浅克隆超时，无法验证模型是否可用（可能是网络问题）'
            )
        except FileNotFoundError:
            logger.error('Git command not found')
            return response_fail(msg='系统未安装git，无法验证模型')
        except Exception as e:
            logger.error(f'Error during shallow clone: {str(e)}')
            # If error occurs, cannot verify if model is available
            return response_success(
                data=None,
                msg=f'模型在OpenCSG Hub中存在且有http_clone_url，但验证过程出错（{str(e)}），无法确认模型是否可用'
            )
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f'Cleaned up temp directory: {temp_dir}')
                except Exception as e:
                    logger.warning(f'Failed to clean up temp directory {temp_dir}: {str(e)}')
        
    except requests.RequestException as e:
        logger.error(f'Failed to request OpenCSG API: {str(e)}')
        return response_fail(msg=f'无法连接到OpenCSG Hub API: {str(e)}')
    except Exception as e:
        logger.error(f'Error checking model: {str(e)}')
        return response_fail(msg=f'检查模型时发生错误: {str(e)}')


@router.get("/list-models", summary="获取模型列表")
def list_models(
    page: int = Query(1, description="页码，从1开始"),
    per_page: int = Query(16, description="每页数量，默认16条"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort: str = Query("trending", description="排序方式")
):
    """
    Fetch model list from OpenCSG Hub and return basic information.
    
    Returns:
    - path: Model path
    - updated_at: Last update time
    - first_tag: show_name of the first tag with category == "task"
    - downloads: Download count
    - description: Model description
    
    :param page: Page number
    :param per_page: Items per page, default 16
    :param search: Search keyword (optional)
    :param sort: Sort method, default trending
    :return: Model list
    """
    try:
        # Get CSGHUB_ENDPOINT from environment
        csghub_endpoint = os.getenv('CSGHUB_ENDPOINT', 'https://hub.opencsg.com')
        api_url = f'{csghub_endpoint}/api/v1/models'
        
        # Set request parameters
        params = {
            'page': page,
            'per': per_page,
            'search': search or '',
            'sort': sort,
            'source': ''
        }
        
        logger.info(f'Fetching models from {api_url} with params: {params}')
        
        # Send request
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Extract required fields
        models_data = []
        if data.get('data'):
            for model in data['data']:
                # Find the first tag with category == "task" and get its show_name
                first_tag_show_name = ''
                if model.get('tags'):
                    for tag in model['tags']:
                        if tag.get('category') == 'task':
                            first_tag_show_name = tag.get('show_name', '')
                            break
                
                model_info = {
                    'path': model.get('path', ''),
                    'updated_at': model.get('updated_at', ''),
                    'first_tag': first_tag_show_name,
                    'downloads': model.get('downloads', 0),
                    'description': model.get('description', '')
                }
                models_data.append(model_info)
        
        # Build result
        result = {
            'models': models_data,
            'total': data.get('total', 0),
            'page': page,
            'per_page': per_page
        }
        
        logger.info(f'Successfully fetched {len(models_data)} models')
        return response_success(data=result, msg='获取模型列表成功')
        
    except requests.RequestException as e:
        logger.error(f'Failed to request OpenCSG API: {str(e)}')
        return response_fail(msg=f'无法连接到OpenCSG Hub API: {str(e)}')
    except Exception as e:
        logger.error(f'Error fetching models: {str(e)}')
        return response_fail(msg=f'获取模型列表时发生错误: {str(e)}')
