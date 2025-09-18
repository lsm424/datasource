from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import uvicorn
import json

from app.core.config import settings
from app.core.database import create_tables
from app.api import api_router
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import setup_middleware
from app.services.scheduler import init_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    await create_tables()
    
    # 启动数据统计调度器
    if settings.ENABLE_SCHEDULER:
        init_scheduler()
    
    yield
    
    # 关闭时执行（清理资源等）
    if settings.ENABLE_SCHEDULER:
        shutdown_scheduler()


def create_application() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
        lifespan=lifespan,
    )
    
    # 设置CORS中间件
    # 开发环境：允许所有来源
    if settings.ENVIRONMENT == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 允许所有来源
            allow_credentials=True,  # 允许携带凭证（包括Authorization头）
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # 生产环境：使用配置的允许列表
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # 禁用压缩中间件（解决gzip问题）
    @app.middleware("http") 
    async def disable_compression(request: Request, call_next):
        response = await call_next(request)
        # 移除可能导致压缩的响应头
        if "content-encoding" in response.headers:
            del response.headers["content-encoding"]
        # 强制设置为不压缩
        response.headers["content-encoding"] = "identity"
        return response
    
    # 添加请求调试中间件
    # 调试中间件已移除
    
    # 设置自定义中间件
    setup_middleware(app)
    
    # 添加422验证错误调试处理器（必须在setup_exception_handlers之前）
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理422验证错误"""
        # 返回详细的422响应
        from fastapi.responses import JSONResponse
        response = JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )
        # 确保没有压缩
        response.headers["content-encoding"] = "identity" 
        return response
    
    # 设置异常处理器（放在自定义异常处理器之后）
    setup_exception_handlers(app)
    
    # 注册API路由
    app.include_router(api_router, prefix="/api/v1")
    
    # 静态文件服务（如果需要）
    if settings.SERVE_STATIC_FILES:
        import os
        static_dir = "static"
        if not os.path.exists(static_dir):
            os.makedirs(static_dir, exist_ok=True)
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    return app


app = create_application()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.ACCESS_LOG,
    )
