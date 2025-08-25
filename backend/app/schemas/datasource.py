from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

from app.models.datasource import DataSourceType, DatabaseType


class FilesystemConfig(BaseModel):
    """文件系统配置模型"""
    path: str = Field(..., description="文件系统路径")
    encoding: Optional[str] = Field("utf-8", description="文件编码")
    extensions: Optional[List[str]] = Field(None, description="允许的文件扩展名")
    
    @validator('path')
    def validate_path(cls, v):
        if not v or not v.strip():
            raise ValueError('路径不能为空')
        return v.strip()


class DatabaseConfig(BaseModel):
    """数据库配置模型"""
    db_type: DatabaseType = Field(..., description="数据库类型")
    host: str = Field(..., description="数据库主机")
    port: int = Field(..., ge=1, le=65535, description="端口号")
    database: str = Field(..., description="数据库名")
    user: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    charset: Optional[str] = Field("utf8", description="字符集")
    ssl: Optional[bool] = Field(False, description="是否使用SSL")
    connection_timeout: Optional[int] = Field(30, ge=5, le=300, description="连接超时时间（秒）")
    
    @validator('host')
    def validate_host(cls, v):
        if not v or not v.strip():
            raise ValueError('主机地址不能为空')
        return v.strip()
    
    @validator('database')
    def validate_database(cls, v):
        if not v or not v.strip():
            raise ValueError('数据库名不能为空')
        return v.strip()
    
    @validator('user')
    def validate_user(cls, v):
        if not v or not v.strip():
            raise ValueError('用户名不能为空')
        return v.strip()


class ObjectStorageConfig(BaseModel):
    """对象存储配置模型"""
    bucket: str = Field(..., description="存储桶名称")
    endpoint: str = Field(..., description="端点地址")
    access_key: str = Field(..., description="访问密钥")
    secret_key: str = Field(..., description="密钥")
    region: Optional[str] = Field(None, description="区域")
    ssl: Optional[bool] = Field(True, description="是否使用SSL")
    
    @validator('bucket')
    def validate_bucket(cls, v):
        if not v or not v.strip():
            raise ValueError('存储桶名称不能为空')
        return v.strip()
    
    @validator('endpoint')
    def validate_endpoint(cls, v):
        if not v or not v.strip():
            raise ValueError('端点地址不能为空')
        # 简单的URL格式验证
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('端点地址必须以http://或https://开头')
        return v.strip()
    
    @validator('access_key')
    def validate_access_key(cls, v):
        if not v or not v.strip():
            raise ValueError('访问密钥不能为空')
        return v.strip()
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v or not v.strip():
            raise ValueError('密钥不能为空')
        return v.strip()


class DataSourceBase(BaseModel):
    """数据源基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="数据源名称")
    cname: str = Field(..., min_length=1, max_length=100, description="中文名称")
    company: Optional[str] = Field(None, max_length=100, description="单位/公司")
    source: Optional[str] = Field(None, max_length=100, description="来源")
    type: DataSourceType = Field(..., description="数据源类型")
    desc: Optional[str] = Field(None, max_length=1000, description="描述")
    tags: Optional[List[str]] = Field(None, description="标签")


class DataSourceCreate(DataSourceBase):
    """创建数据源模型"""
    config: Union[FilesystemConfig, DatabaseConfig, ObjectStorageConfig] = Field(..., description="连接配置")
    
    @validator('config', pre=True)
    def validate_config(cls, v, values):
        if 'type' not in values:
            return v
        
        data_type = values['type']
        if data_type == DataSourceType.FILESYSTEM:
            return FilesystemConfig(**v) if isinstance(v, dict) else v
        elif data_type == DataSourceType.DATABASE:
            return DatabaseConfig(**v) if isinstance(v, dict) else v
        elif data_type == DataSourceType.OBJECT_STORAGE:
            return ObjectStorageConfig(**v) if isinstance(v, dict) else v
        
        return v


class DataSourceUpdate(BaseModel):
    """更新数据源模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="数据源名称")
    cname: Optional[str] = Field(None, min_length=1, max_length=100, description="中文名称")
    company: Optional[str] = Field(None, max_length=100, description="单位/公司")
    source: Optional[str] = Field(None, max_length=100, description="来源")
    desc: Optional[str] = Field(None, max_length=1000, description="描述")
    config: Optional[Union[FilesystemConfig, DatabaseConfig, ObjectStorageConfig]] = Field(None, description="连接配置")
    is_active: Optional[bool] = Field(None, description="是否激活")
    tags: Optional[List[str]] = Field(None, description="标签")


class DataSourceInDB(DataSourceBase):
    """数据库中的数据源模型"""
    id: str = Field(..., description="数据源ID")
    num: int = Field(0, description="文件数或记录数")
    size: int = Field(0, description="数据大小（字节）")
    config: Dict[str, Any] = Field(..., description="连接配置")
    is_active: bool = Field(True, description="是否激活")
    is_connected: bool = Field(False, description="是否已连接")
    last_test_at: Optional[datetime] = Field(None, description="最后测试时间")
    last_test_status: Optional[str] = Field(None, description="最后测试状态")
    last_test_message: Optional[str] = Field(None, description="最后测试消息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")
    
    class Config:
        from_attributes = True


class DataSourcePublic(DataSourceBase):
    """公开数据源信息模型"""
    id: str = Field(..., description="数据源ID")
    num: int = Field(0, description="文件数或记录数")
    size: int = Field(0, description="数据大小（字节）")
    is_active: bool = Field(True, description="是否激活")
    is_connected: bool = Field(False, description="是否已连接")
    last_test_at: Optional[datetime] = Field(None, description="最后测试时间")
    last_test_status: Optional[str] = Field(None, description="最后测试状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class ConnectionTest(BaseModel):
    """连接测试模型"""
    type: DataSourceType = Field(..., description="数据源类型")
    config: Union[FilesystemConfig, DatabaseConfig, ObjectStorageConfig] = Field(..., description="连接配置")


class ConnectionTestResult(BaseModel):
    """连接测试结果模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="测试消息")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")
    duration: Optional[float] = Field(None, description="测试耗时（秒）")


class DataSourceStats(BaseModel):
    """数据源统计模型"""
    total_count: int = Field(0, description="总数")
    type_stats: Dict[str, int] = Field(default_factory=dict, description="类型统计")
    active_count: int = Field(0, description="活跃数量")
    connected_count: int = Field(0, description="已连接数量")
    total_size: int = Field(0, description="总数据大小")
    total_items: int = Field(0, description="总项目数")


class FileSystemItem(BaseModel):
    """文件系统项目模型"""
    name: str = Field(..., description="名称")
    path: str = Field(..., description="路径")
    type: str = Field(..., description="类型（file/directory）")
    size: int = Field(0, description="大小（字节）")
    modified_at: datetime = Field(..., description="修改时间")
    permissions: Optional[str] = Field(None, description="权限")
    extension: Optional[str] = Field(None, description="扩展名")


class DatabaseTable(BaseModel):
    """数据库表模型"""
    name: str = Field(..., description="表名")
    schema: Optional[str] = Field(None, description="模式名")
    row_count: int = Field(0, description="行数")
    comment: Optional[str] = Field(None, description="注释")


class DatabaseColumn(BaseModel):
    """数据库列模型"""
    name: str = Field(..., description="列名")
    type: str = Field(..., description="数据类型")
    nullable: bool = Field(True, description="是否可空")
    default_value: Optional[str] = Field(None, description="默认值")
    comment: Optional[str] = Field(None, description="注释")
    is_primary_key: bool = Field(False, description="是否主键")
    is_auto_increment: bool = Field(False, description="是否自增")


class DatabaseRecord(BaseModel):
    """数据库记录模型"""
    # 使用Dict来表示动态的记录数据，因为不同表的字段不同
    data: Dict[str, Any] = Field(..., description="记录数据")


class ObjectStorageObject(BaseModel):
    """对象存储对象模型"""
    key: str = Field(..., description="对象键")
    size: int = Field(0, description="大小（字节）")
    last_modified: datetime = Field(..., description="最后修改时间")
    etag: str = Field(..., description="ETag")
    storage_class: Optional[str] = Field(None, description="存储类型")
    content_type: Optional[str] = Field(None, description="内容类型")
    is_folder: Optional[bool] = Field(False, description="是否为文件夹")


class DataSourceListQuery(BaseModel):
    """数据源列表查询模型"""
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    type: Optional[DataSourceType] = Field(None, description="类型筛选")
    is_active: Optional[bool] = Field(None, description="激活状态筛选")
    search: Optional[str] = Field(None, description="搜索关键词")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="排序方向")
