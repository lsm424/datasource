from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional, Any
from datetime import datetime

T = TypeVar('T')


class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(200, description="响应代码")
    message: str = Field("success", description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class DataResponse(BaseResponse, Generic[T]):
    """数据响应模型"""
    data: T = Field(..., description="响应数据")


class ListResponse(BaseResponse, Generic[T]):
    """列表响应模型"""
    data: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总数")
    page: int = Field(1, description="页码")
    limit: int = Field(20, description="每页数量")
    total_pages: int = Field(..., description="总页数")
    
    @classmethod
    def create(cls, data: List[T], total: int, page: int, limit: int):
        """创建分页响应"""
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        return cls(
            data=data,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )


class PageRequest(BaseModel):
    """分页请求模型"""
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    search: Optional[str] = Field(None, description="搜索关键词")


class SortRequest(BaseModel):
    """排序请求模型"""
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="排序方向")


class FilterRequest(BaseModel):
    """过滤请求模型"""
    filters: Optional[dict] = Field(None, description="过滤条件")


class BulkRequest(BaseModel, Generic[T]):
    """批量操作请求模型"""
    items: List[T] = Field(..., description="操作项目列表")


class BulkResponse(BaseResponse):
    """批量操作响应模型"""
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")


class StatusResponse(BaseResponse):
    """状态响应模型"""
    status: str = Field(..., description="状态")
    details: Optional[dict] = Field(None, description="详细信息")


class ErrorDetail(BaseModel):
    """错误详情模型"""
    field: Optional[str] = Field(None, description="错误字段")
    message: str = Field(..., description="错误消息")
    code: Optional[str] = Field(None, description="错误代码")


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    code: int = Field(..., ge=400, description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[List[ErrorDetail]] = Field(None, description="错误详情")
    trace_id: Optional[str] = Field(None, description="追踪ID")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field("healthy", description="服务状态")
    version: str = Field(..., description="版本号")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    services: Optional[dict] = Field(None, description="依赖服务状态")
    uptime: Optional[float] = Field(None, description="运行时间（秒）")
