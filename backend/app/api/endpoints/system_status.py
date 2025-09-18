"""
系统状态监控API
提供异步任务执行状态、系统性能指标等信息
"""
from fastapi import APIRouter, Depends
from typing import Any, Dict
import asyncio
import time
from datetime import datetime

from app.core.deps import get_current_admin_user
from app.models.user import User
from app.schemas.base import DataResponse
from app.core.async_executor import async_executor

router = APIRouter()

@router.get("/task-status", response_model=DataResponse[Dict[str, Any]])
async def get_async_task_status(
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """获取异步任务执行状态（仅管理员）"""
    
    try:
        # 获取异步执行器状态
        task_info = async_executor.get_running_tasks_info()
        
        # 获取系统异步事件循环状态
        loop = asyncio.get_event_loop()
        
        # 构建状态信息
        status_info = {
            "async_executor": {
                "max_workers": async_executor.max_workers,
                "timeout": async_executor.timeout,
                "total_tasks": task_info["total_tasks"],
                "running_tasks": len(task_info["running_tasks"]),
                "completed_tasks": task_info["completed_tasks"],
                "failed_tasks": task_info["failed_tasks"],
                "running_task_details": task_info["running_tasks"]
            },
            "event_loop": {
                "is_running": loop.is_running(),
                "is_closed": loop.is_closed()
            },
            "system": {
                "timestamp": datetime.now().isoformat(),
                "uptime_info": "System monitoring active"
            }
        }
        
        return DataResponse(
            data=status_info,
            message="系统任务状态获取成功"
        )
        
    except Exception as e:
        return DataResponse(
            data={
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            message="获取系统任务状态失败"
        )


@router.get("/performance", response_model=DataResponse[Dict[str, Any]])
async def get_system_performance(
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """获取系统性能指标（仅管理员）"""
    
    try:
        import psutil
        import os
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        
        # 进程信息
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        performance_info = {
            "cpu": {
                "usage_percent": cpu_percent,
                "core_count": psutil.cpu_count(),
                "logical_count": psutil.cpu_count(logical=True)
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "usage_percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "usage_percent": (disk.used / disk.total) * 100
            },
            "process": {
                "pid": os.getpid(),
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "cpu_percent": process.cpu_percent(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
            },
            "async_tasks": async_executor.get_running_tasks_info(),
            "timestamp": datetime.now().isoformat()
        }
        
        return DataResponse(
            data=performance_info,
            message="系统性能指标获取成功"
        )
        
    except ImportError:
        return DataResponse(
            data={
                "error": "psutil 库未安装，无法获取详细的系统性能信息",
                "async_tasks": async_executor.get_running_tasks_info(),
                "timestamp": datetime.now().isoformat()
            },
            message="系统性能指标获取失败"
        )
    except Exception as e:
        return DataResponse(
            data={
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            message="获取系统性能指标失败"
        )


@router.post("/task-cleanup", response_model=DataResponse[Dict[str, Any]])
async def cleanup_completed_tasks(
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """清理已完成的任务记录（仅管理员）"""
    
    try:
        before_count = len(async_executor.running_tasks)
        
        # 清理已完成的任务（保留最近的20个）
        if before_count > 20:
            sorted_tasks = sorted(
                async_executor.running_tasks.items(),
                key=lambda x: x[1].get("start_time", 0)
            )
            async_executor.running_tasks = dict(sorted_tasks[-20:])
        
        after_count = len(async_executor.running_tasks)
        
        cleanup_info = {
            "tasks_before": before_count,
            "tasks_after": after_count,
            "cleaned_count": before_count - after_count,
            "timestamp": datetime.now().isoformat()
        }
        
        return DataResponse(
            data=cleanup_info,
            message="任务记录清理完成"
        )
        
    except Exception as e:
        return DataResponse(
            data={
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            message="任务记录清理失败"
        )
