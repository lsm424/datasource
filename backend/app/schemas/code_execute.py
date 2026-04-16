"""代码执行相关 Schema"""
from typing import List, Optional
from pydantic import BaseModel, Field


class CodeExecuteRequest(BaseModel):
    """代码执行请求"""
    code: str = Field(..., description="要执行的Python代码")
    timeout: Optional[int] = Field(default=30, description="超时时间(秒)", ge=1, le=300)


class CodeExecuteResponse(BaseModel):
    """代码执行响应"""
    success: bool = Field(..., description="是否执行成功")
    stdout: str = Field(default="", description="标准输出内容")
    stderr: str = Field(default="", description="标准错误输出内容")
    images: List[str] = Field(default_factory=list, description="Base64编码的图片列表")
    error: Optional[str] = Field(default=None, description="错误信息(异常堆栈)")
