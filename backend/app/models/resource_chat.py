"""资源分析对话会话与消息模型"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ResourceChatSession(Base):
    """资源分析对话会话（按用户+资源唯一）"""
    __tablename__ = "resource_chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), nullable=False, index=True)
    resource_key = Column(String(512), nullable=False, index=True)
    resource_display_name = Column(String(256), nullable=False)
    datasource_type = Column(String(32), nullable=False)
    datasource_id = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ResourceChatMessage(Base):
    """资源分析对话消息"""
    __tablename__ = "resource_chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
