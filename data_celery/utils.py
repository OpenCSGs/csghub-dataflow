import os,socket,shutil
from loguru import logger
from datetime import datetime

def ensure_directory_exists(directory: str) -> None:

    if not os.path.exists(directory):
        os.makedirs(directory)
def ensure_directory_exists_remove(directory: str) -> None:

    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)


from pathlib import Path

def log_info(p1,p2) -> None:

    pass


def log_error(p1, p2) -> None:

    pass


def get_project_root() -> Path:

    current_file_path = Path(__file__).resolve()

    while not (current_file_path / 'setup.py').exists():
        if current_file_path.parent == current_file_path:

            raise FileNotFoundError(
                "Project root not found. Make sure there is a 'setup.py' or '__init__.py' in the project root.")
        current_file_path = current_file_path.parent

    return current_file_path

def get_datasource_log_path(task_uid: str) -> str:

    project_root_path = get_project_root()
    log_file_path = f"{project_root_path}/datasource/log/{task_uid}.log"
    return log_file_path


def get_format_folder_path(task_uid:str):

    project_root_path = get_project_root()
    format_folder_path = f"{project_root_path}/temp_format/{task_uid}"
    return format_folder_path

def get_datasource_temp_parquet_dir(task_uid: str) -> str:

    project_root_path = get_project_root()
    temp_json_dir_path = f"{project_root_path}/datasource/parquet/{task_uid}"
    return temp_json_dir_path

def get_pipline_temp_job_dir(job_uid: str) -> str:

    project_root_path = get_project_root()
    temp_dir_path = f"{project_root_path}/temp_pipline/yaml/{job_uid}"
    return temp_dir_path


def get_datasource_csg_hub_server_dir(task_uid: str) -> str:

    project_root_path = get_project_root()
    temp_json_dir_path = f"{project_root_path}/datasource/csg_hub_server/{task_uid}"
    return temp_json_dir_path

def get_current_ip() -> str:

    s = None
    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        s.connect(('8.8.8.8', 80))

        ip_address = s.getsockname()[0]
    except Exception as e:

        print(f"Error getting IP address: {e}")
        ip_address = None
    finally:

        if s is not None:
            s.close()

    return ip_address



def get_current_time():

    return datetime.now()


def get_timestamp():

    return int(datetime.timestamp(datetime.now()))


