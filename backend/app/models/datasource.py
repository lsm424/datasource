from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, JSON, Enum
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import uuid
import json

from app.core.database import Base


class DataSourceType(PyEnum):
    """数据源类型枚举"""
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    OBJECT_STORAGE = "object_storage"


class DatabaseType(PyEnum):
    """数据库类型枚举"""
    MYSQL = "MySQL"
    POSTGRESQL = "PostgreSQL"
    SQLITE = "SQLite"
    ORACLE = "Oracle"
    SQLSERVER = "SQLServer"


class DataSource(Base):
    """数据源模型"""
    __tablename__ = "datasources"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(100), nullable=False, comment="数据源名称")
    cname = Column(String(100), nullable=False, comment="中文名称")
    company = Column(String(100), nullable=True, comment="单位/公司")
    source = Column(String(100), nullable=True, comment="来源")
    type = Column(Enum(DataSourceType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True, comment="数据源类型")
    desc = Column(Text, nullable=True, comment="描述")
    
    # 统计信息
    num = Column(Integer, default=0, comment="文件数或记录数")
    size = Column(Integer, default=0, comment="数据大小（字节）")
    
    # 连接配置（JSON格式存储）
    config = Column(JSON, nullable=False, comment="连接配置")
    
    # 状态字段
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_connected = Column(Boolean, default=False, nullable=False, comment="是否已连接")
    last_test_at = Column(DateTime(timezone=True), nullable=True, comment="最后测试时间")
    last_test_status = Column(String(20), nullable=True, comment="最后测试状态")
    last_test_message = Column(Text, nullable=True, comment="最后测试消息")
    
    # 时间字段
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 扩展字段
    tags = Column(JSON, nullable=True, comment="标签（JSON数组）")
    extra_metadata = Column(JSON, nullable=True, comment="额外元数据")
    
    def __repr__(self):
        return f"<DataSource(id='{self.id}', name='{self.name}', type='{self.type.value}')>"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "cname": self.cname,
            "company": self.company,
            "source": self.source,
            "type": self.type.value,
            "desc": self.desc,
            "num": self.num,
            "size": self.size,
            "config": self.config,
            "is_active": self.is_active,
            "is_connected": self.is_connected,
            "last_test_at": self.last_test_at.isoformat() if self.last_test_at else None,
            "last_test_status": self.last_test_status,
            "last_test_message": self.last_test_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": self.tags or [],
            "extra_metadata": self.extra_metadata or {},
        }
    
    def get_filesystem_config(self) -> dict:
        """获取文件系统配置"""
        if self.type != DataSourceType.FILESYSTEM:
            raise ValueError("Not a filesystem datasource")
        return self.config
    
    def get_database_config(self) -> dict:
        """获取数据库配置"""
        if self.type != DataSourceType.DATABASE:
            raise ValueError("Not a database datasource")
        return self.config
    
    def get_object_storage_config(self) -> dict:
        """获取对象存储配置"""
        if self.type != DataSourceType.OBJECT_STORAGE:
            raise ValueError("Not an object storage datasource")
        return self.config
    
    def update_stats(self, num: int = None, size: int = None):
        """更新统计信息"""
        if num is not None:
            self.num = num
        if size is not None:
            self.size = size
    
    def update_connection_status(self, is_connected: bool, message: str = None):
        """更新连接状态"""
        self.is_connected = is_connected
        self.last_test_at = func.now()
        self.last_test_status = "success" if is_connected else "failed"
        self.last_test_message = message
    
    def add_tag(self, tag: str):
        """添加标签"""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str):
        """移除标签"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def set_metadata(self, key: str, value):
        """设置元数据"""
        if not self.extra_metadata:
            self.extra_metadata = {}
        self.extra_metadata[key] = value
    
    def get_metadata(self, key: str, default=None):
        """获取元数据"""
        if not self.extra_metadata:
            return default
        return self.extra_metadata.get(key, default)
