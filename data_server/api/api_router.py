from fastapi import APIRouter

from .endpoints import job, operator, operator_permission, algo_templates
from .endpoints import template
from .endpoints import task_log
from .endpoints import op
from .endpoints import tool
from .endpoints import agent
from .endpoints import datasource
from .endpoints import formatify
from .endpoints import op_pic_upload
from .endpoints import celery_server
from .endpoints import jump_to_studio

api_router = APIRouter(prefix="/api/v1/dataflow")

api_router.include_router(job.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(task_log.router, prefix="/task_log", tags=["任务日志相关接口"])
api_router.include_router(template.router, prefix="/templates", tags=["Templates"])
api_router.include_router(op.router, prefix="/ops", tags=["Operators"])
api_router.include_router(tool.router, prefix="/tools", tags=["Tools"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
api_router.include_router(datasource.router, prefix="/datasource", tags=["Datasource"])
api_router.include_router(formatify.router, prefix="/formatify", tags=["Formatify"])
api_router.include_router(celery_server.router, prefix="/celery", tags=["Celery 相关接口"])
api_router.include_router(jump_to_studio.router, prefix="/studio", tags=["Studio"])

api_router.include_router(operator.router, prefix="/operator", tags=["算子相关接口"])
api_router.include_router(operator_permission.router, prefix="/operator_permission", tags=["算子权限相关接口"])

api_router.include_router(op_pic_upload.op_pic_router, prefix="/internal_api", tags=["文件上传接口"])

api_router.include_router(algo_templates.router, prefix="/algo_templates", tags=["算法模板相关接口"])
