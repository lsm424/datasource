from typing import Union
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError
import traceback
import logging

from app.core.config import settings
from app.schemas.base import ErrorResponse, ErrorDetail

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataBrowserException(Exception):
    """自定义应用异常基类"""
    
    def __init__(
        self,
        message: str,
        code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: list = None
    ):
        self.message = message
        self.code = code
        self.details = details or []
        super().__init__(self.message)


class ValidationException(DataBrowserException):
    """验证异常"""
    
    def __init__(self, message: str, details: list = None):
        super().__init__(
            message=message,
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class AuthenticationException(DataBrowserException):
    """认证异常"""
    
    def __init__(self, message: str = "认证失败"):
        super().__init__(
            message=message,
            code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationException(DataBrowserException):
    """授权异常"""
    
    def __init__(self, message: str = "权限不足"):
        super().__init__(
            message=message,
            code=status.HTTP_403_FORBIDDEN
        )


class ResourceNotFoundException(DataBrowserException):
    """资源不存在异常"""
    
    def __init__(self, message: str = "资源不存在"):
        super().__init__(
            message=message,
            code=status.HTTP_404_NOT_FOUND
        )


class ResourceConflictException(DataBrowserException):
    """资源冲突异常"""
    
    def __init__(self, message: str = "资源冲突"):
        super().__init__(
            message=message,
            code=status.HTTP_409_CONFLICT
        )


class DataSourceException(DataBrowserException):
    """数据源异常"""
    
    def __init__(self, message: str, code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message=message, code=code)


class ConnectionException(DataSourceException):
    """连接异常"""
    
    def __init__(self, message: str = "数据源连接失败"):
        super().__init__(message=message, code=status.HTTP_503_SERVICE_UNAVAILABLE)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    error_response = ErrorResponse(
        code=exc.status_code,
        message=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response.model_dump())
    )


async def starlette_http_exception_handler(
    request: Request, 
    exc: StarletteHTTPException
) -> JSONResponse:
    """Starlette HTTP异常处理器"""
    error_response = ErrorResponse(
        code=exc.status_code,
        message=str(exc.detail)
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response.model_dump())
    )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """请求验证异常处理器"""
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:]) if len(error["loc"]) > 1 else str(error["loc"][0])
        details.append(
            ErrorDetail(
                field=field,
                message=error["msg"],
                code=error["type"]
            )
        )
    
    error_response = ErrorResponse(
        code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="请求参数验证失败",
        details=details
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response.model_dump())
    )


async def databrowser_exception_handler(
    request: Request,
    exc: DataBrowserException
) -> JSONResponse:
    """自定义应用异常处理器"""
    error_response = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=[ErrorDetail(message=detail) for detail in exc.details] if exc.details else None
    )
    return JSONResponse(
        status_code=exc.code,
        content=jsonable_encoder(error_response.model_dump())
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: Union[IntegrityError, OperationalError]
) -> JSONResponse:
    """SQLAlchemy异常处理器"""
    logger.error(f"Database error: {exc}")
    
    if isinstance(exc, IntegrityError):
        # 数据库完整性错误（如唯一约束违反）
        message = "数据完整性错误，可能存在重复的数据"
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, OperationalError):
        # 数据库操作错误（如连接失败）
        message = "数据库操作失败"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        message = "数据库错误"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    error_response = ErrorResponse(
        code=status_code,
        message=message
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(error_response.model_dump())
    )


async def pydantic_validation_exception_handler(
    request: Request,
    exc: ValidationError
) -> JSONResponse:
    """Pydantic验证异常处理器"""
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        details.append(
            ErrorDetail(
                field=field,
                message=error["msg"],
                code=error["type"]
            )
        )
    
    error_response = ErrorResponse(
        code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="数据验证失败",
        details=details
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response.model_dump())
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    # 在开发环境显示详细错误信息
    if settings.ENVIRONMENT == "development":
        message = f"{type(exc).__name__}: {str(exc)}"
    else:
        message = "服务器内部错误"
    
    error_response = ErrorResponse(
        code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(error_response.model_dump())
    )


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""
    
    # HTTP异常
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    
    # 验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    
    # 自定义异常
    app.add_exception_handler(DataBrowserException, databrowser_exception_handler)
    
    # 数据库异常
    app.add_exception_handler(IntegrityError, sqlalchemy_exception_handler)
    app.add_exception_handler(OperationalError, sqlalchemy_exception_handler)
    
    # 通用异常（必须放在最后）
    app.add_exception_handler(Exception, generic_exception_handler)
