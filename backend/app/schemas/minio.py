"""
MinIO对象存储相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class BucketInfo(BaseModel):
    """存储桶信息"""
    name: str = Field(..., description="存储桶名称")
    creation_date: Optional[str] = Field(None, description="创建时间")
    region: str = Field("us-east-1", description="区域")

class ObjectInfo(BaseModel):
    """对象信息"""
    key: str = Field(..., description="对象键名")
    size: int = Field(0, description="对象大小（字节）")
    last_modified: Optional[str] = Field(None, description="最后修改时间")
    etag: str = Field("", description="ETag")
    content_type: str = Field("application/octet-stream", description="内容类型")
    is_dir: bool = Field(False, description="是否为目录")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class CreateBucketRequest(BaseModel):
    """创建存储桶请求"""
    name: str = Field(..., min_length=3, max_length=63, description="存储桶名称")
    region: Optional[str] = Field("us-east-1", description="区域")

class UploadObjectRequest(BaseModel):
    """上传对象请求"""
    bucket_name: str = Field(..., description="存储桶名称")
    object_name: str = Field(..., description="对象名称")
    content_type: Optional[str] = Field("application/octet-stream", description="内容类型")

class DeleteObjectRequest(BaseModel):
    """删除对象请求"""
    bucket_name: str = Field(..., description="存储桶名称")
    object_name: str = Field(..., description="对象名称")

class ListObjectsQuery(BaseModel):
    """列出对象查询参数"""
    prefix: Optional[str] = Field("", description="对象前缀")
    delimiter: Optional[str] = Field("", description="分隔符")
    max_keys: Optional[int] = Field(1000, ge=1, le=10000, description="最大返回数量")

class UploadResult(BaseModel):
    """上传结果"""
    bucket_name: str = Field(..., description="存储桶名称")
    object_name: str = Field(..., description="对象名称")
    etag: str = Field(..., description="ETag")
    version_id: Optional[str] = Field(None, description="版本ID")
    size: Optional[int] = Field(None, description="文件大小")

class MinIOConnectionTest(BaseModel):
    """MinIO连接测试结果"""
    success: bool = Field(..., description="连接是否成功")
    message: str = Field(..., description="连接消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="连接详情")
