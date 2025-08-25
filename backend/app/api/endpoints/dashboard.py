from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import Any, List, Optional
from datetime import datetime, timedelta

from app.core.deps import get_current_active_user, get_current_admin_user, get_db
from app.models.user import User
from app.models.datasource import DataSource
from app.models.data_stats import DailyStats, DataSourceStats, StatsTask
from app.schemas.base import DataResponse
from app.services.data_stats_service import DataStatsService
from app.services.scheduler import stats_scheduler

router = APIRouter()


@router.get("/stats", response_model=DataResponse[dict])
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取仪表盘统计数据（基于最新的每日统计）"""
    
    # 获取最新的每日统计数据
    latest_stats = db.query(DailyStats).order_by(desc(DailyStats.stats_date)).first()
    
    if latest_stats:
        stats = {
            "total_datasources": latest_stats.total_datasources,
            "total_users": 0,
            "total_data_size": latest_stats.total_data_size,
            "total_files": latest_stats.total_files,
            "total_records": latest_stats.total_records,
            "stats_date": latest_stats.stats_date.isoformat(),
            "is_admin": current_user.is_admin
        }
    else:
        # 如果没有统计数据，使用实时数据作为后备
        datasources = db.query(DataSource).filter(DataSource.is_active == True).all()
        stats = {
            "total_datasources": len(datasources),
            "total_users": 0,
            "total_data_size": sum(ds.size or 0 for ds in datasources),
            "total_files": sum(ds.num or 0 for ds in datasources),
            "total_records": 0,
            "stats_date": None,
            "is_admin": current_user.is_admin
        }
    
    # 用户统计（仅管理员可见）
    if current_user.is_admin:
        user_count = db.query(User).filter(User.is_active == True).count()
        stats["total_users"] = user_count
    
    return DataResponse(
        data=stats,
        message="获取仪表盘统计成功"
    )


@router.get("/type-distribution", response_model=DataResponse[dict])
async def get_type_distribution(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取数据类型分布"""
    
    # 获取最新的每日统计数据
    latest_stats = db.query(DailyStats).order_by(desc(DailyStats.stats_date)).first()
    
    if latest_stats and latest_stats.type_distribution:
        distribution = latest_stats.type_distribution
        
        # 转换为图表数据格式
        chart_data = []
        for type_name, type_data in distribution.items():
            if type_data['count'] > 0:  # 只显示有数据的类型
                chart_data.append({
                    'name': {
                        'filesystem': '文件系统',
                        'database': '数据库',
                        'object_storage': '对象存储'
                    }.get(type_name, type_name),
                    'value': type_data['size'],
                    'count': type_data['count'],
                    'type': type_name
                })
        
        return DataResponse(
            data={
                'distribution': chart_data,
                'stats_date': latest_stats.stats_date.isoformat()
            },
            message="获取数据类型分布成功"
        )
    else:
        # 使用实时数据作为后备
        filesystem_count = db.query(DataSource).filter(
            and_(DataSource.is_active == True, DataSource.type == 'filesystem')
        ).count()
        
        database_count = db.query(DataSource).filter(
            and_(DataSource.is_active == True, DataSource.type == 'database')
        ).count()
        
        object_storage_count = db.query(DataSource).filter(
            and_(DataSource.is_active == True, DataSource.type == 'object_storage')
        ).count()
        
        chart_data = []
        if filesystem_count > 0:
            chart_data.append({'name': '文件系统', 'value': 0, 'count': filesystem_count, 'type': 'filesystem'})
        if database_count > 0:
            chart_data.append({'name': '数据库', 'value': 0, 'count': database_count, 'type': 'database'})
        if object_storage_count > 0:
            chart_data.append({'name': '对象存储', 'value': 0, 'count': object_storage_count, 'type': 'object_storage'})
        
        return DataResponse(
            data={
                'distribution': chart_data,
                'stats_date': None
            },
            message="获取数据类型分布成功（实时数据）"
        )


@router.get("/datasource-distribution", response_model=DataResponse[dict])
async def get_datasource_distribution(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50, description="返回数据源数量限制")
) -> Any:
    """获取数据源分布（按数据大小排序）"""
    
    # 获取最新的每日统计数据
    latest_stats = db.query(DailyStats).order_by(desc(DailyStats.stats_date)).first()
    
    if latest_stats and latest_stats.datasource_distribution:
        distribution = latest_stats.datasource_distribution[:limit]  # 取前N个
        
        return DataResponse(
            data={
                'distribution': distribution,
                'stats_date': latest_stats.stats_date.isoformat()
            },
            message="获取数据源分布成功"
        )
    else:
        # 使用实时数据作为后备
        datasources = db.query(DataSource).filter(DataSource.is_active == True).all()
        
        distribution = []
        for ds in sorted(datasources, key=lambda x: x.size or 0, reverse=True)[:limit]:
            distribution.append({
                'name': ds.name,
                'type': ds.type.value if ds.type else 'unknown',
                'size': ds.size or 0,
                'records': 0,  # 实时数据中没有记录数
                'files': ds.num or 0
            })
        
        return DataResponse(
            data={
                'distribution': distribution,
                'stats_date': None
            },
            message="获取数据源分布成功（实时数据）"
        )


@router.get("/system-status", response_model=DataResponse[dict])
async def get_system_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取系统状态信息"""
    
    # 检查数据库连接状态
    try:
        db.execute("SELECT 1")
        database_status = True
    except Exception:
        database_status = False
    
    # 获取调度器状态
    scheduler_status = stats_scheduler.get_scheduler_status()
    
    # 获取最近的统计任务状态
    recent_task = db.query(StatsTask).order_by(desc(StatsTask.created_at)).first()
    
    status = {
        "database": database_status,
        "cache": False,  # 暂时未实现缓存
        "version": "1.0.0",
        "scheduler": scheduler_status,
        "last_stats_task": {
            "status": recent_task.status if recent_task else "unknown",
            "date": recent_task.task_date.isoformat() if recent_task else None,
            "duration": recent_task.duration_seconds if recent_task else None
        } if recent_task else None
    }
    
    return DataResponse(
        data=status,
        message="获取系统状态成功"
    )


@router.post("/run-stats", response_model=DataResponse[dict])
async def run_manual_stats(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    target_date: Optional[str] = Query(None, description="统计日期 (YYYY-MM-DD)")
) -> Any:
    """手动执行统计任务（仅管理员）"""
    
    try:
        # 解析目标日期
        if target_date:
            target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
        else:
            target_datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 检查是否已有相同日期的任务在运行
        existing_task = db.query(StatsTask).filter(
            and_(
                StatsTask.task_date == target_datetime,
                StatsTask.status.in_(["pending", "running"])
            )
        ).first()
        
        if existing_task:
            raise HTTPException(
                status_code=400, 
                detail=f"日期 {target_date or 'today'} 的统计任务已在运行中"
            )
        
        # 在后台执行统计任务
        background_tasks.add_task(
            stats_scheduler.run_manual_stats,
            target_datetime
        )
        
        return DataResponse(
            data={
                "target_date": target_datetime.isoformat(),
                "status": "started"
            },
            message="统计任务已启动，请稍后查看结果"
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动统计任务失败: {str(e)}")


@router.get("/stats-history", response_model=DataResponse[List[dict]])
async def get_stats_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="历史天数")
) -> Any:
    """获取历史统计数据"""
    
    start_date = datetime.now() - timedelta(days=days)
    
    history_stats = db.query(DailyStats).filter(
        DailyStats.stats_date >= start_date
    ).order_by(desc(DailyStats.stats_date)).all()
    
    history_data = []
    for stats in history_stats:
        history_data.append({
            "date": stats.stats_date.isoformat(),
            "total_datasources": stats.total_datasources,
            "total_data_size": stats.total_data_size,
            "total_files": stats.total_files,
            "total_records": stats.total_records,
            "filesystem_size": stats.filesystem_size,
            "database_size": stats.database_size,
            "object_storage_size": stats.object_storage_size
        })
    
    return DataResponse(
        data=history_data,
        message=f"获取最近{days}天统计历史成功"
    )
