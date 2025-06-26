from fastapi import APIRouter

from .endpoints import job
from .endpoints import template
from .endpoints import op
from .endpoints import tool
from .endpoints import agent

api_router = APIRouter(prefix="/api/v1/dataflow")

api_router.include_router(job.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(template.router, prefix="/templates", tags=["Templates"])
api_router.include_router(op.router, prefix="/ops", tags=["Operators"])
api_router.include_router(tool.router, prefix="/tools", tags=["Tools"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
