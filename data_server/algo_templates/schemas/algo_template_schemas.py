from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AlgoTemplateBase(BaseModel):
    """算法模板基础模型"""
    user_id: Optional[str] = Field(None, max_length=255, description="用户id")
    name: Optional[str] = Field(None, max_length=255, description="算法模块名称")
    description: Optional[str] = Field(None, max_length=255, description="算法模版描述")
    type: Optional[str] = Field(None, max_length=255, description="算法模版类型")
    buildin: Optional[bool] = Field(False, description="是否为内置模版")
    project_name: Optional[str] = Field("dataflow-demo-process", max_length=255, description="项目名称")
    dataset_path: Optional[str] = Field("/path/to/your/dataset", max_length=255, description="输入数据集路径")
    exprot_path: Optional[str] = Field("/path/to/your/dataset.jsonl", max_length=255, description="输出数据集路径")
    np: Optional[str] = Field(3, max_length=255, description="并行处理的进程数，控制CPU使用和处理速度")
    open_tracer: Optional[bool] = Field(True, description="是否开启操作追踪，用于调试和性能分析")
    trace_num: Optional[str] = Field(3, max_length=255, description="追踪的样本数量，每个操作追踪多少个样本的处理过程")
    backend_yaml: Optional[str] = Field(None, description="后端yaml格式")
    dslText: Optional[str] = Field(None, description="前端yaml格式")


class AlgoTemplateCreate(AlgoTemplateBase):
    """创建算法模板的请求模型"""
    name: str = Field(..., max_length=255, description="算法模块名称")
    type: str = Field(..., max_length=255, description="算法模版类型")


class AlgoTemplateUpdate(AlgoTemplateBase):
    """更新算法模板的请求模型"""
    id: int = Field(..., description="模板ID")


class AlgoTemplateResponse(AlgoTemplateBase):
    """算法模板响应模型"""
    id: int = Field(..., description="主键id")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_dat: Optional[datetime] = Field(None, description="修改时间")

    class Config:
        from_attributes = True
        orm_mode = True


class AlgoTemplateQuery(BaseModel):
    """算法模板查询参数模型"""
    name: Optional[str] = Field(None, description="算法模块名称（模糊查询）")
    type: Optional[str] = Field(None, description="算法模版类型过滤")
    buildin: Optional[bool] = Field(None, description="是否为内置模版过滤")
    user_id: Optional[str] = Field(None, description="用户id")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")


# 导出所有schemas
__all__ = [
    "AlgoTemplateBase",
    "AlgoTemplateCreate",
    "AlgoTemplateUpdate", 
    "AlgoTemplateResponse",
    "AlgoTemplateQuery"
]
