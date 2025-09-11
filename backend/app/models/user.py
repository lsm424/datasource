from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text, JSON
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import uuid

from app.core.database import Base


class UserRole(PyEnum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    name = Column(String(100), nullable=False, comment="真实姓名")
    hashed_password = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False, comment="用户角色")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_verified = Column(Boolean, default=False, nullable=False, comment="是否已验证邮箱")
    
    # 时间字段
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment="最后登录时间")
    
    # 扩展字段
    avatar = Column(String(500), nullable=True, comment="头像URL")
    phone = Column(String(20), nullable=True, comment="手机号")
    company = Column(String(100), nullable=True, comment="公司/组织")
    bio = Column(Text, nullable=True, comment="个人简介")
    
    # SSO相关字段
    external_id = Column(String(200), nullable=True, unique=True, index=True, comment="外部系统用户ID")
    extra_metadata = Column(JSON, nullable=True, comment="扩展元数据")
    
    def __repr__(self):
        return f"<User(id='{self.id}', username='{self.username}', role='{self.role.value}')>"
    
    @property
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role == UserRole.ADMIN
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "avatar": self.avatar,
            "phone": self.phone,
            "company": self.company,
            "bio": self.bio,
            "external_id": self.external_id,
            "extra_metadata": self.extra_metadata,
        }
