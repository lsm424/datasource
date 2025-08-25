from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import time
import psutil
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db, check_database_connection
from app.schemas.base import HealthResponse, DataResponse

router = APIRouter()

# 应用启动时间
APP_START_TIME = time.time()


@router.get("/", response_model=DataResponse[HealthResponse])
async def health_check(db: Session = Depends(get_db)):
    """健康检查端点"""
    
    # 检查数据库连接
    db_healthy = check_database_connection()
    
    # 检查Redis连接（如果启用）
    redis_healthy = True
    if settings.REDIS_ENABLED:
        try:
            # TODO: 实现Redis连接检查
            pass
        except Exception:
            redis_healthy = False
    
    # 系统信息
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage('/')
    
    # 应用运行时间
    uptime = time.time() - APP_START_TIME
    
    # 确定整体状态
    overall_status = "healthy"
    if not db_healthy or not redis_healthy:
        overall_status = "unhealthy"
    elif cpu_percent > 90 or memory_info.percent > 90 or disk_info.percent > 95:
        overall_status = "warning"
    
    services = {
        "database": {
            "status": "healthy" if db_healthy else "unhealthy",
            "connection": db_healthy
        },
        "redis": {
            "status": "healthy" if redis_healthy else "unhealthy", 
            "enabled": settings.REDIS_ENABLED,
            "connection": redis_healthy
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_info.percent,
            "disk_percent": disk_info.percent,
            "available_memory_mb": memory_info.available / (1024 * 1024)
        }
    }
    
    health_data = HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        timestamp=datetime.now(),
        services=services,
        uptime=uptime
    )
    
    return DataResponse(
        code=200 if overall_status == "healthy" else 503,
        message=f"服务状态: {overall_status}",
        data=health_data
    )


@router.get("/ping")
async def ping():
    """简单的ping端点"""
    return {"message": "pong", "timestamp": datetime.now()}


@router.get("/info")
async def app_info():
    """应用信息端点"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.PROJECT_DESCRIPTION,
        "environment": settings.ENVIRONMENT,
        "uptime": time.time() - APP_START_TIME,
        "timestamp": datetime.now()
    }
