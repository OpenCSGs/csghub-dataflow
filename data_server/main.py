from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from data_server.database.session import initialize_database
from data_server.api.api_router import api_router
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from loguru import logger
#from data_server.agent.deps import init_managers, cleanup_managers
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

        # Initialize managers (DB, Connection, Team)
        #await init_managers()
        logger.info("Managers initialized successfully")

        # _scheduler = BackgroundScheduler()
        # _scheduler.add_job(
        #     func=celery_status_scheduled_task,
        #     trigger=IntervalTrigger(seconds=3),
        #     id='celery_status_scheduled_task',
        #     name='celery_status_scheduled_task Task',
        #     replace_existing=True
        #
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

        # Initialize database data
        initialize_database()

        # Fix orphaned jobs after service restart
        from data_server.job.JobHealthCheck import fix_orphaned_jobs
        try:
            fix_result = fix_orphaned_jobs()
            logger.info(
                f"Orphaned jobs check completed: "
                f"{fix_result['fixed_count']} jobs fixed, "
                f"{fix_result['skipped_count']} jobs still running"
            )
        except Exception as fix_error:
            logger.error(f"Failed to fix orphaned jobs during startup: {str(fix_error)}")
            # Don't interrupt startup process

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
 #       await cleanup_managers()
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
    

    response = await call_next(request)
    
    
    logger.info("-" * 50)
    
    return response

app.include_router(api_router)


# Sets all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

