import os,socket,shutil
from loguru import logger
from datetime import datetime

def ensure_directory_exists(directory: str) -> None:
    """
    确保指定的目录存在，如果不存在则创建它

    Args:
        directory (str): 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
def ensure_directory_exists_remove(directory: str) -> None:
    """
    确保指定的目录存在，如果不存在则创建它
    Args:
        directory (str): 目录路径
    """
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)


from pathlib import Path

def log_info(p1,p2) -> None:
    """
    初始化日志配置
    """
    pass


def log_error(p1, p2) -> None:
    """
    初始化日志配置
    """
    pass


def get_project_root() -> Path:
    """
    获取项目根目录的路径
    Returns:
        Path: 项目根目录的路径
    """
    # 获取当前文件的绝对路径
    current_file_path = Path(__file__).resolve()
    # 向上遍历目录，直到找到指定的标记文件或目录（例如，通常项目根目录会有 setup.py 或 __init__.py）
    while not (current_file_path / 'setup.py').exists():
        if current_file_path.parent == current_file_path:
            # 防止无限循环，当到达文件系统的根目录时停止
            raise FileNotFoundError(
                "Project root not found. Make sure there is a 'setup.py' or '__init__.py' in the project root.")
        current_file_path = current_file_path.parent

    return current_file_path

def get_datasource_log_path(task_uid: str) -> str:
    """
    获取数据源日志路径
    Args:
        task_uid (str): 任务UID
    Returns:
        str: 数据源日志路径
    """
    project_root_path = get_project_root()
    log_file_path = f"{project_root_path}/datasource/log/{task_uid}.log"
    return log_file_path


def get_format_folder_path(task_uid:str):
    """
    获取格式化任务文件夹路径
    Args:
        task_uid (str): 任务UID
    Returns:
        str: 格式化任务文件夹路径
    """
    project_root_path = get_project_root()
    format_folder_path = f"{project_root_path}/temp_format/{task_uid}"
    return format_folder_path

def get_datasource_temp_parquet_dir(task_uid: str) -> str:
    """
    获取数据源临时json文件目录
    Args:
        task_uid (str): 任务UID
    Returns:
        str: 数据源临时json文件目录
    """
    project_root_path = get_project_root()
    temp_json_dir_path = f"{project_root_path}/datasource/parquet/{task_uid}"
    return temp_json_dir_path

def get_pipline_temp_job_dir(job_uid: str) -> str:
    """
    获取任务yaml文件夹路径
    Args:
        job_uid (str): 任务UID
    Returns:
        str: 任务yaml文件夹路径
    """
    project_root_path = get_project_root()
    temp_dir_path = f"{project_root_path}/temp_pipline/yaml/{job_uid}"
    return temp_dir_path


def get_datasource_csg_hub_server_dir(task_uid: str) -> str:
    """
    获取csg_hub_server上传时的临时目录
    Args:
        task_uid (str): 任务UID
    Returns:
        str: 数据源临时json文件目录
    """
    project_root_path = get_project_root()
    temp_json_dir_path = f"{project_root_path}/datasource/csg_hub_server/{task_uid}"
    return temp_json_dir_path

def get_current_ip() -> str:
    """
    获取当前机器的 IP 地址

    Returns:
        str: 当前机器的 IP 地址，如果无法获取则返回 None
    """
    s = None  # 初始化 s 为 None
    try:
        # 创建一个 socket 对象
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到外部服务器以触发本地 IP 地址的分配
        s.connect(('8.8.8.8', 80))
        # 获取本地地址信息
        ip_address = s.getsockname()[0]
    except Exception as e:
        # 如果出现错误，打印错误信息
        print(f"Error getting IP address: {e}")
        ip_address = None
    finally:
        # 关闭 socket 连接，如果它已经被创建
        if s is not None:
            s.close()

    return ip_address



def get_current_time():
    """
    获取当前时间

    Returns:
        datetime: 当前时间的 datetime 对象
    """
    return datetime.now()


def get_timestamp():
    """
    获取当前时间戳

    Returns:
        int: 当前时间戳
    """
    return int(datetime.timestamp(datetime.now()))


