"""
数据模型包

导入所有模型以确保它们被SQLAlchemy识别和创建
"""

from .user import User, UserRole
from .datasource import DataSource, DataSourceType, DatabaseType
from .data_stats import DataSourceStats, DailyStats, StatsTask
from .role import Role, RoleDatasetPermission
from .resource_chat import ResourceChatSession, ResourceChatMessage

__all__ = [
    "User",
    "UserRole",
    "DataSource",
    "DataSourceType",
    "DatabaseType",
    "DataSourceStats",
    "DailyStats",
    "StatsTask",
    "Role",
    "RoleDatasetPermission",
    "ResourceChatSession",
    "ResourceChatMessage",
]
