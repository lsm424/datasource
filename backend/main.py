from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 设置自定义中间件
    setup_middleware(app)
    
    # 设置异常处理器
    setup_exception_handlers(app)
    
    # 注册API路由
    app.include_router(api_router, prefix="/api/v1")
    
    # 静态文件服务（如果需要）
    if settings.SERVE_STATIC_FILES:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
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
