from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Role(Base):
    """数据访问角色"""
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(100), nullable=False, unique=True, comment="角色名称")
    code = Column(String(50), nullable=False, unique=True, comment="角色编码")
    description = Column(Text, nullable=True, comment="角色描述")
    built_in = Column(Boolean, nullable=False, default=False, comment="是否内置角色（不可删除）")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class RoleDatasetPermission(Base):
    """角色-数据集权限"""
    __tablename__ = "role_dataset_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    role_id = Column(String(36), nullable=False, comment="角色ID")
    datasource_id = Column(String(36), nullable=False, index=True, comment="数据源ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

