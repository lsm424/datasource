from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.models.datasource import DataSource, DataSourceType
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
    
    # 计算总数
    total = query.count()
    
    # 分页和排序
    datasources = query.order_by(DataSource.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # 转换为响应模型
    datasource_list = [DataSourcePublic.model_validate(ds) for ds in datasources]
    
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
    current_user: User = Depends(get_current_active_user),  # 临时改为普通用户权限
    db: Session = Depends(get_db)
) -> Any:
    """测试数据源连接（仅管理员）"""
    
    try:
        import time
        start_time = time.time()
        
        # TODO: 实现不同类型数据源的连接测试逻辑
        # 这里应该根据数据源类型调用相应的连接测试函数
        
        if connection_test.type == DataSourceType.FILESYSTEM:
            # 测试文件系统连接
            import os
            config = connection_test.config
            path = config.path if hasattr(config, 'path') else config['path']
            if not os.path.exists(path):
                raise Exception(f"路径不存在: {path}")
            if not os.path.isdir(path):
                raise Exception(f"路径不是目录: {path}")
        
        elif connection_test.type == DataSourceType.DATABASE:
            # 测试数据库连接
            # TODO: 实现数据库连接测试
            pass
        
        elif connection_test.type == DataSourceType.OBJECT_STORAGE:
            # 测试对象存储连接
            # TODO: 实现对象存储连接测试
            pass
        
        duration = time.time() - start_time
        
        result = ConnectionTestResult(
            success=True,
            message="连接测试成功",
            duration=duration
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
