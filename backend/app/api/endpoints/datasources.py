from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.models.datasource import DataSource, DataSourceType
from app.models.role import RoleDatasetPermission
from app.models.data_stats import DataSourceStats as DataSourceStatsModel
from app.schemas.datasource import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceInDB,
    DataSourcePublic,
    ConnectionTest,
    ConnectionTestResult,
    DataSourceStats,
    DataSourceListQuery
)
from app.schemas.base import DataResponse, ListResponse, BaseResponse
from app.services.data_stats_service import DataStatsService

router = APIRouter()


@router.get("/", response_model=ListResponse[DataSourcePublic])
async def get_datasources(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: DataSourceType = Query(None),
    is_active: bool = Query(None),
    search: str = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取数据源列表"""
    
    query = db.query(DataSource)
    
    # 类型筛选
    if type:
        query = query.filter(DataSource.type == type)
    
    # 活跃状态筛选
    if is_active is not None:
        query = query.filter(DataSource.is_active == is_active)
    
    # 搜索
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (DataSource.name.like(search_pattern)) |
            (DataSource.cname.like(search_pattern)) |
            (DataSource.company.like(search_pattern)) |
            (DataSource.desc.like(search_pattern))
        )

    # 非管理员按数据访问角色过滤可见数据源
    if not current_user.is_admin:
        if not getattr(current_user, "role_id", None):
            # 未绑定数据访问角色则无任何数据源
            return ListResponse.create(data=[], total=0, page=page, limit=limit)
        query = (
            query.join(
                RoleDatasetPermission,
                DataSource.id == RoleDatasetPermission.datasource_id,
            )
            .filter(RoleDatasetPermission.role_id == current_user.role_id)
            .distinct()
        )
    
    # 计算总数
    total = query.count()
    
    # 分页和排序
    datasources = query.order_by(DataSource.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # 转换为响应模型并添加统计信息
    datasource_list = []
    for ds in datasources:
        ds_data = DataSourcePublic.model_validate(ds)
        
        # 获取最新的统计信息（严格按时间顺序，显示最新的数据）
        latest_stats = db.query(DataSourceStatsModel).filter(
            DataSourceStatsModel.datasource_id == ds.id,
            DataSourceStatsModel.status == "completed"
        ).order_by(
            DataSourceStatsModel.stats_date.desc(),
            DataSourceStatsModel.created_at.desc()
        ).first()
        
        if latest_stats:
            # 使用统计表中的数据，根据数据源类型选择合适的字段
            if ds.type == DataSourceType.DATABASE:
                # 数据库：项目数 = 记录数
                ds_data.num = latest_stats.record_count
            else:
                # 文件系统和对象存储：项目数 = 文件数
                ds_data.num = latest_stats.file_count
            
            # 数据量统一使用数据大小
            ds_data.size = latest_stats.data_size
        else:
            # 如果没有统计信息，保持原有值（通常为0）
            pass
            
        datasource_list.append(ds_data)
    
    return ListResponse.create(
        data=datasource_list,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/statistics", response_model=DataResponse[DataSourceStats])
async def get_datasource_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取数据源统计信息"""
    
    # 总数统计
    total_count = db.query(DataSource).count()
    active_count = db.query(DataSource).filter(DataSource.is_active == True).count()
    connected_count = db.query(DataSource).filter(DataSource.is_connected == True).count()
    
    # 按类型统计
    type_stats = {}
    for ds_type in DataSourceType:
        count = db.query(DataSource).filter(DataSource.type == ds_type).count()
        type_stats[ds_type.value] = count
    
    # 计算总数据大小和项目数
    result = db.query(
        db.func.sum(DataSource.size).label('total_size'),
        db.func.sum(DataSource.num).label('total_items')
    ).first()
    
    total_size = result.total_size or 0
    total_items = result.total_items or 0
    
    stats = DataSourceStats(
        total_count=total_count,
        type_stats=type_stats,
        active_count=active_count,
        connected_count=connected_count,
        total_size=total_size,
        total_items=total_items
    )
    
    return DataResponse(
        data=stats,
        message="获取统计信息成功"
    )


@router.get("/{datasource_id}", response_model=DataResponse[DataSourceInDB])
async def get_datasource(
    datasource_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """根据ID获取数据源详情"""
    
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在"
        )
    
    # 对于非管理员用户，隐藏敏感配置信息
    datasource_data = DataSourceInDB.model_validate(datasource)
    if not current_user.is_admin:
        # 隐藏密码等敏感信息
        config = datasource_data.config.copy()
        if 'password' in config:
            config['password'] = '***'
        if 'secret_key' in config:
            config['secret_key'] = '***'
        datasource_data.config = config
    
    return DataResponse(
        data=datasource_data,
        message="获取数据源信息成功"
    )


@router.post("/", response_model=DataResponse[DataSourcePublic])
async def create_datasource(
    datasource_create: DataSourceCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """创建数据源（仅管理员）"""
    
    # 检查名称是否已存在
    if db.query(DataSource).filter(DataSource.name == datasource_create.name).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="数据源名称已存在"
        )
    
    # 创建数据源 - 使用mode='json'来正确序列化枚举类型
    datasource_data = datasource_create.model_dump(mode='json')
    
    # 确保config字段也被正确序列化
    if "config" in datasource_data and hasattr(datasource_create.config, "model_dump"):
        datasource_data["config"] = datasource_create.config.model_dump(mode='json')
    
    new_datasource = DataSource(**datasource_data)
    db.add(new_datasource)
    db.commit()
    db.refresh(new_datasource)
    
    datasource_response = DataSourcePublic.model_validate(new_datasource)
    
    return DataResponse(
        data=datasource_response,
        message="数据源创建成功"
    )


@router.put("/{datasource_id}", response_model=DataResponse[DataSourcePublic])
async def update_datasource(
    datasource_id: str,
    datasource_update: DataSourceUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """更新数据源（仅管理员）"""
    
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在"
        )
    
    # 检查名称是否已被其他数据源使用
    if datasource_update.name and datasource_update.name != datasource.name:
        existing_datasource = db.query(DataSource).filter(
            DataSource.name == datasource_update.name,
            DataSource.id != datasource_id
        ).first()
        if existing_datasource:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="数据源名称已被使用"
            )
    
    # 更新数据源信息 - 使用mode='json'来正确序列化枚举类型
    update_data = datasource_update.model_dump(exclude_unset=True, mode='json')
    if "config" in update_data and hasattr(datasource_update.config, "model_dump"):
        update_data["config"] = datasource_update.config.model_dump(mode='json')
    
    for field, value in update_data.items():
        setattr(datasource, field, value)
    
    db.commit()
    db.refresh(datasource)
    
    datasource_data = DataSourcePublic.model_validate(datasource)
    
    return DataResponse(
        data=datasource_data,
        message="数据源更新成功"
    )


@router.delete("/{datasource_id}", response_model=BaseResponse)
async def delete_datasource(
    datasource_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """删除数据源（仅管理员）"""
    
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在"
        )
    
    db.delete(datasource)
    db.commit()
    
    return BaseResponse(message="数据源删除成功")


@router.post("/test-connection", response_model=DataResponse[ConnectionTestResult])
async def test_datasource_connection(
    connection_test: ConnectionTest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """测试数据源连接（异步执行，不阻塞系统）"""
    
    from app.core.async_executor import run_in_background
    from app.services.minio_service import create_minio_service_with_retry
    import time
    
    def _test_filesystem_connection(config_dict):
        """在线程中测试文件系统连接（同步函数）"""
        import os
        path = config_dict.get('path')
        if not path:
            raise Exception("文件系统路径不能为空")
        if not os.path.exists(path):
            raise Exception(f"路径不存在: {path}")
        if not os.path.isdir(path):
            raise Exception(f"路径不是目录: {path}")
        
        # 测试读取权限
        try:
            os.listdir(path)
        except PermissionError:
            raise Exception(f"没有权限访问路径: {path}")
        
        return {"accessible": True, "path": path}
    
    def _test_database_connection(config_dict):
        """在线程中测试数据库连接（同步函数）"""
        db_type = config_dict.get('db_type', 'MySQL')
        
        # 处理枚举类型，转换为字符串
        if hasattr(db_type, 'value'):
            db_type = db_type.value
        
        if db_type == 'MySQL':
            import pymysql
            connection = pymysql.connect(
                host=config_dict.get('host', 'localhost'),
                port=config_dict.get('port', 3306),
                user=config_dict.get('user', 'root'),
                password=config_dict.get('password', ''),
                database=config_dict.get('database', ''),
                connect_timeout=10,
                charset='utf8mb4'
            )
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            connection.close()
        elif db_type == 'SQLite':
            import sqlite3
            db_path = config_dict.get('database', '')
            if not db_path:
                raise Exception("SQLite数据库文件路径不能为空")
            connection = sqlite3.connect(db_path, timeout=10)
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            connection.close()
        elif db_type == 'PostgreSQL':
            import psycopg2
            connection = psycopg2.connect(
                host=config_dict.get('host', 'localhost'),
                port=config_dict.get('port', 5432),
                user=config_dict.get('user', 'postgres'),
                password=config_dict.get('password', ''),
                database=config_dict.get('database', ''),
                connect_timeout=10
            )
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            connection.close()
        else:
            raise Exception(f"不支持的数据库类型: {db_type}")
        
        return {"connected": True, "db_type": db_type}
    
    async def _test_object_storage_connection(config_dict):
        """测试对象存储连接"""
        service = create_minio_service_with_retry(config_dict)
        result = await service.test_connection_async()
        if not result["success"]:
            raise Exception(result["message"])
        return result["details"]
    
    try:
        start_time = time.time()
        
        # 将配置转换为字典格式
        config_dict = connection_test.config.dict() if hasattr(connection_test.config, 'dict') else connection_test.config
        
        # 根据数据源类型异步执行连接测试
        if connection_test.type == DataSourceType.FILESYSTEM:
            details = await run_in_background(
                _test_filesystem_connection,
                config_dict,
                timeout=30
            )
        
        elif connection_test.type == DataSourceType.DATABASE:
            details = await run_in_background(
                _test_database_connection,
                config_dict,
                timeout=30
            )
        
        elif connection_test.type == DataSourceType.OBJECT_STORAGE:
            details = await _test_object_storage_connection(config_dict)
        
        else:
            raise Exception(f"不支持的数据源类型: {connection_test.type}")
        
        duration = time.time() - start_time
        
        result = ConnectionTestResult(
            success=True,
            message="连接测试成功",
            duration=duration,
            details=details
        )
        
        return DataResponse(
            data=result,
            message="连接测试完成"
        )
        
    except Exception as e:
        duration = time.time() - start_time
        result = ConnectionTestResult(
            success=False,
            message=f"连接测试失败: {str(e)}",
            duration=duration
        )
        
        return DataResponse(
            data=result,
            message="连接测试完成"
        )


@router.post("/{datasource_id}/stats", response_model=DataResponse[dict])
async def run_datasource_stats(
    datasource_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """运行单个数据源的统计任务"""
    
    # 获取数据源
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在"
        )
    
    # 检查数据源是否激活
    if not datasource.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="数据源未激活，无法执行统计"
        )
    
    try:
        # 在后台执行统计任务
        background_tasks.add_task(
            _run_single_datasource_stats_task,
            datasource_id,
            db.connection().engine
        )
        
        return DataResponse(
            data={
                "datasource_id": datasource_id,
                "datasource_name": datasource.name,
                "status": "started"
            },
            message=f"数据源 {datasource.name} 的统计任务已启动"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动统计任务失败: {str(e)}"
        )


async def _run_single_datasource_stats_task(datasource_id: str, engine):
    """后台执行单个数据源统计任务（异步执行，不阻塞系统）"""
    from sqlalchemy.orm import sessionmaker
    from app.services.data_stats_service import DataStatsService
    from app.core.async_executor import async_executor
    import logging
    
    logger = logging.getLogger(__name__)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    try:
        with SessionLocal() as db:
            # 获取数据源
            datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
            if not datasource:
                logger.error(f"数据源不存在: {datasource_id}")
                return
            
            logger.info(f"🚀 开始异步统计数据源: {datasource.name}")
            
            # 创建统计服务实例
            stats_service = DataStatsService(db)
            
            # 使用当前时间作为统计日期
            stats_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            try:
                # 在异步执行器中执行统计任务
                result = await stats_service._calculate_single_datasource(datasource, stats_date)
                
                if result:
                    logger.info(f"✅ 数据源统计完成: {datasource.name}")
                else:
                    logger.error(f"❌ 数据源统计失败: {datasource.name}")
                    
            except asyncio.TimeoutError:
                logger.error(f"⏰ 数据源统计超时: {datasource.name}")
            except Exception as stats_error:
                logger.error(f"❌ 数据源统计异常: {datasource.name}, 错误: {stats_error}")
    
    except Exception as e:
        logger.error(f"❌ 执行单个数据源统计任务失败: {e}")
        
    finally:
        # 记录任务完成状态
        logger.info(f"📊 数据源统计任务结束: {datasource_id}")
        
        # 输出当前运行任务状态（用于监控）
        task_info = async_executor.get_running_tasks_info()
        if task_info["running_tasks"]:
            logger.info(f"📈 当前运行中的统计任务: {len(task_info['running_tasks'])} 个")


@router.get("/{datasource_id}/stats", response_model=DataResponse[dict])
async def get_datasource_stats(
    datasource_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50, description="返回记录数量")
) -> Any:
    """获取单个数据源的统计历史"""
    
    # 获取数据源
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在"
        )
    
    # 获取该数据源的已完成统计记录（按时间倒序）
    stats_records = db.query(DataSourceStatsModel).filter(
        DataSourceStatsModel.datasource_id == datasource_id,
        DataSourceStatsModel.status == "completed"
    ).order_by(
        DataSourceStatsModel.stats_date.desc(),
        DataSourceStatsModel.created_at.desc()
    ).limit(limit).all()
    
    # 转换为字典格式
    stats_history = []
    for record in stats_records:
        stats_history.append({
            "id": record.id,
            "stats_date": record.stats_date.isoformat(),
            "record_count": record.record_count,
            "data_size": record.data_size,
            "file_count": record.file_count,
            "status": record.status,
            "error_message": record.error_message,
            "created_at": record.created_at.isoformat() if record.created_at else None
        })
    
    # 获取最新的统计记录作为当前状态
    latest_stats = stats_records[0] if stats_records else None
    current_stats = None
    if latest_stats:
        current_stats = {
            "record_count": latest_stats.record_count,
            "data_size": latest_stats.data_size,
            "file_count": latest_stats.file_count,
            "last_updated": latest_stats.stats_date.isoformat(),
            "status": latest_stats.status
        }
    
    return DataResponse(
        data={
            "datasource_id": datasource_id,
            "datasource_name": datasource.name,
            "current_stats": current_stats,
            "history": stats_history,
            "total_records": len(stats_history)
        },
        message="获取数据源统计信息成功"
    )
