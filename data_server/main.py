from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from data_server.api.api_router import api_router
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from loguru import logger
from data_server.agent.deps import init_managers, cleanup_managers
import threading
import os

_stop_event: threading.Event = None
_workflow_thread: threading.Thread = None


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
        await init_managers()
        logger.info("Managers initialized successfully")

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

# Sets all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

