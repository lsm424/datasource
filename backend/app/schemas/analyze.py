"""资源分析对话相关 Schema"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """创建/获取会话"""
    resource_key: str = Field(..., alias="resourceKey", description="资源唯一键")
    resource_display_name: str = Field(..., alias="resourceDisplayName", description="资源显示名")
    datasource_type: str = Field(..., alias="datasourceType", description="filesystem | object_storage | database")
    datasource_id: str = Field(..., alias="datasourceId", description="数据源ID")

    model_config = {"populate_by_name": True}


class SessionPublic(BaseModel):
    """会话信息"""
    id: str
    user_id: str
    resource_key: str
    resource_display_name: str
    datasource_type: str
    datasource_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessagePublic(BaseModel):
    """单条消息"""
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """发送对话请求"""
    content: str = Field(..., description="用户输入内容")
