from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from data_server.api.api_router import api_router
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from loguru import logger
from data_server.agent.deps import init_managers, cleanup_managers
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from data_celery.main import celery_app
from data_celery.redis_tools.tools import (celery_server_status_is_exists,get_celery_server_list,
                                           del_celery_server_list)
from data_celery.utils import get_project_root
import threading
import os

from data_server.api.endpoints.op_pic_upload import op_pic_router

_stop_event: threading.Event = None
_workflow_thread: threading.Thread = None


def celery_status_scheduled_task():
    """
    定时检测celery状态
    """
    try:
        pass
    except Exception as e:
        logger.error(f"celery_status_scheduled_task 定时任务执行出错: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifecycle manager for the FastAPI application.
    Handles initialization and cleanup of application resources.
    """
    # Startup
    logger.info("Initializing application...")
    try:
        # setup_s3_storage()
        # logger.info("S3 storage initialized successfully")

        # 初始化雪花ID生成器
        from data_server.utils.id_generator import register_id_generator_listeners
        from data_server.database.bean.base import Base
        register_id_generator_listeners(Base)
        logger.info("Snowflake ID generator initialized successfully")

        # Initialize managers (DB, Connection, Team)
        await init_managers()
        logger.info("Managers initialized successfully")
        # 初始化定时任务调度器
        # _scheduler = BackgroundScheduler()
        # _scheduler.add_job(
        #     func=celery_status_scheduled_task,
        #     trigger=IntervalTrigger(seconds=3),  # 每3秒执行一次
        #     id='celery_status_scheduled_task',
        #     name='celery_status_scheduled_task Task',
        #     replace_existing=True
        # )
        # _scheduler.start()
        # logger.info("APScheduler started with scheduled task (every 3 seconds)")

        if os.getenv("WORKFLOW_ENABLED", "False") == "True":
            from data_server.job.JobWorkflow import watch_dataflow_resources
            from data_server.job.JobWorkflowExecutor import resource_callback
            _stop_event = threading.Event()
            namespace = os.getenv("WORKFLOW_NAMESPACE", "data-flow")
            _workflow_thread = watch_dataflow_resources(
                namespace=namespace,
                callback=resource_callback,
                stop_event=_stop_event
            )
            logger.info("Resource workflow watcher initialized successfully")

        # Any other initialization code
        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

    yield  # Application runs here

    # Shutdown
    try:
        logger.info("Initiating shutdown sequence...")
        if os.getenv("WORKFLOW_ENABLED", "False") == "True":
            if _stop_event:
                _stop_event.set()
                if _workflow_thread:
                    _workflow_thread.join(timeout=5) 
                    if _workflow_thread.is_alive():
                        logger.warning("Workflow thread did not terminate gracefully")


        logger.info("Cleaning up application resources...")
        await cleanup_managers()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

app = FastAPI(
    title="Data Flow API Server",
    version="1.0.0",
    description="",
    openapi_url="/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    path = request.url.path
    method = request.method
    client_host = request.client.host if request.client else "unknown"

    logger.info(f"Request: {method} {path}. Client: {client_host}")
    logger.info(f"Headers: {dict(request.headers)}")

    if method in ["POST", "PUT"]:
        try:
            body = await request.body()
            if body:
                logger.info(f"Request Body: {body.decode()}")
        except Exception as e:
            logger.warning(f"Could not read request body: {e}")
    
    # 执行请求
    response = await call_next(request)
    
    
    logger.info("-" * 50)
    
    return response

app.include_router(api_router)

# 添加静态文件服务，用于访问上传的文件
from pathlib import Path
uploads_dir = Path(os.path.join(get_project_root(), 'attach'))
# logger.info(f"Uploads directory: {uploads_dir}")
uploads_dir.mkdir(parents=True, exist_ok=True)
# 以files开头的请求，去掉files后拼接到uploads_dir路径下访问文件
app.mount("/files", StaticFiles(directory=str(uploads_dir)), name="files")

# Sets all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

