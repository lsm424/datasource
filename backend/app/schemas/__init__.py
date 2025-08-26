"""
Pydantic schemas 包

用于API请求和响应的数据验证和序列化
"""

from .base import (
    BaseResponse,
    DataResponse, 
    ListResponse,
    PageRequest,
    SortRequest,
    FilterRequest,
    BulkRequest,
    BulkResponse,
    StatusResponse,
    ErrorResponse,
    ErrorDetail,
    HealthResponse
)

from .user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserAdminUpdate,
    UserInDB,
    UserPublic,
    UserLogin,
    UserRegister,
    ChangePassword,
    ResetPassword,
    Token,
    TokenData,
    LoginResponse,
    UserListQuery
)

from .datasource import (
    FilesystemConfig,
    DatabaseConfig,
    ObjectStorageConfig,
    DataSourceBase,
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceInDB,
    DataSourcePublic,
    ConnectionTest,
    ConnectionTestResult,
    DataSourceStats,
    FileSystemItem,
    DatabaseTable,
    DatabaseColumn,
    ObjectStorageObject,
    DataSourceListQuery
)

from .minio import (
    BucketInfo,
    ObjectInfo,
    CreateBucketRequest,
    ListObjectsQuery,
    UploadResult,
    MinIOConnectionTest
)

__all__ = [
    # 基础schemas
    "BaseResponse",
    "DataResponse",
    "ListResponse", 
    "PageRequest",
    "SortRequest",
    "FilterRequest",
    "BulkRequest",
    "BulkResponse",
    "StatusResponse",
    "ErrorResponse",
    "ErrorDetail",
    "HealthResponse",
    
    # 用户schemas
    "UserBase",
    "UserCreate",
    "UserUpdate", 
    "UserAdminUpdate",
    "UserInDB",
    "UserPublic",
    "UserLogin",
    "UserRegister",
    "ChangePassword",
    "ResetPassword",
    "Token",
    "TokenData",
    "LoginResponse",
    "UserListQuery",
    
    # 数据源schemas
    "FilesystemConfig",
    "DatabaseConfig",
    "ObjectStorageConfig",
    "DataSourceBase",
    "DataSourceCreate",
    "DataSourceUpdate",
    "DataSourceInDB",
    "DataSourcePublic",
    "ConnectionTest",
    "ConnectionTestResult",
    "DataSourceStats",
    "FileSystemItem",
    "DatabaseTable",
    "DatabaseColumn",
    "ObjectStorageObject",
    "DataSourceListQuery",
    
    # MinIO schemas
    "BucketInfo",
    "ObjectInfo",
    "CreateBucketRequest",
    "ListObjectsQuery",
    "UploadResult",
    "MinIOConnectionTest"
]
