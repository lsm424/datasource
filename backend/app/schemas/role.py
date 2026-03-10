from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    """角色基础信息"""
    name: str = Field(..., max_length=100, description="角色名称")
    code: str = Field(..., max_length=50, description="角色编码")
    description: Optional[str] = Field(None, description="角色描述")


class RoleCreate(RoleBase):
    """创建角色"""
    pass


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = Field(None, max_length=100, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")


class RolePublic(RoleBase):
    """公开角色信息"""
    id: str = Field(..., description="角色ID")
    built_in: bool = Field(..., description="是否内置角色")
    created_at: datetime = Field(..., alias="createdAt", description="创建时间")
    updated_at: datetime = Field(..., alias="updatedAt", description="更新时间")

    class Config:
        from_attributes = True
        populate_by_name = True


class RoleWithDatasets(RolePublic):
    """带数据权限的角色信息"""
    dataset_ids: List[str] = Field(default_factory=list, alias="datasetIds", description="可访问的数据源ID列表")

