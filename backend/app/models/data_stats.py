from sqlalchemy import Column, String, Integer, BigInteger, DateTime, JSON, Text
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class DataSourceStats(Base):
    """数据源统计表"""
    __tablename__ = "datasource_stats"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, comment="统计ID")
    datasource_id = Column(String(36), nullable=False, index=True, comment="数据源ID")
    datasource_name = Column(String(255), nullable=False, comment="数据源名称")
    datasource_type = Column(String(50), nullable=False, index=True, comment="数据源类型")
    
    # 统计数据
    record_count = Column(BigInteger, default=0, comment="数据条数")
    data_size = Column(BigInteger, default=0, comment="数据大小(字节)")
    file_count = Column(Integer, default=0, comment="文件总数")
    
    # 详细信息
    details = Column(JSON, comment="详细统计信息")
    
    # 时间信息
    stats_date = Column(DateTime(timezone=True), nullable=False, index=True, comment="统计日期")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 状态信息
    status = Column(String(20), default="completed", comment="统计状态")
    error_message = Column(Text, comment="错误信息")
    
    def __repr__(self):
        return f"<DataSourceStats(id='{self.id}', datasource='{self.datasource_name}', date='{self.stats_date}')>"


class DailyStats(Base):
    """每日统计汇总表"""
    __tablename__ = "daily_stats"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, comment="统计ID")
    stats_date = Column(DateTime(timezone=True), nullable=False, unique=True, index=True, comment="统计日期")
    
    # 总体统计
    total_datasources = Column(Integer, default=0, comment="数据源总数")
    total_records = Column(BigInteger, default=0, comment="数据总条数")
    total_data_size = Column(BigInteger, default=0, comment="数据总大小(字节)")
    total_files = Column(Integer, default=0, comment="文件总数")
    
    # 按类型统计
    filesystem_count = Column(Integer, default=0, comment="文件系统数据源数量")
    filesystem_size = Column(BigInteger, default=0, comment="文件系统数据大小")
    filesystem_files = Column(Integer, default=0, comment="文件系统文件数")
    
    database_count = Column(Integer, default=0, comment="数据库数据源数量")
    database_size = Column(BigInteger, default=0, comment="数据库数据大小")
    database_records = Column(BigInteger, default=0, comment="数据库记录数")
    
    object_storage_count = Column(Integer, default=0, comment="对象存储数据源数量")
    object_storage_size = Column(BigInteger, default=0, comment="对象存储数据大小")
    object_storage_files = Column(Integer, default=0, comment="对象存储文件数")
    
    # 详细分布数据
    datasource_distribution = Column(JSON, comment="数据源分布详情")
    type_distribution = Column(JSON, comment="类型分布详情")
    
    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 统计状态
    status = Column(String(20), default="completed", comment="统计状态")
    duration_seconds = Column(Integer, comment="统计耗时(秒)")
    
    def __repr__(self):
        return f"<DailyStats(date='{self.stats_date}', datasources={self.total_datasources})>"


class StatsTask(Base):
    """统计任务记录表"""
    __tablename__ = "stats_tasks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid, comment="任务ID")
    task_type = Column(String(50), nullable=False, comment="任务类型")
    task_date = Column(DateTime(timezone=True), nullable=False, index=True, comment="任务日期")
    
    # 任务状态
    status = Column(String(20), default="pending", comment="任务状态: pending, running, completed, failed")
    
    # 执行信息
    started_at = Column(DateTime(timezone=True), comment="开始时间")
    completed_at = Column(DateTime(timezone=True), comment="完成时间")
    duration_seconds = Column(Integer, comment="执行耗时(秒)")
    
    # 结果信息
    processed_count = Column(Integer, default=0, comment="处理数据源数量")
    success_count = Column(Integer, default=0, comment="成功数量")
    failed_count = Column(Integer, default=0, comment="失败数量")
    
    # 错误信息
    error_message = Column(Text, comment="错误信息")
    error_details = Column(JSON, comment="错误详情")
    
    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self):
        return f"<StatsTask(id='{self.id}', type='{self.task_type}', status='{self.status}')>"
