from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime
from enum import Enum

from app.models.user import UserRole


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$", description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    name: str = Field(..., min_length=1, max_length=100, description="真实姓名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    company: Optional[str] = Field(None, max_length=100, description="公司/组织")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")


class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    role: Optional[UserRole] = Field(UserRole.USER, description="用户角色")
    
    @validator('password')
    def validate_password(cls, v):
        """密码复杂度验证"""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v


class UserUpdate(BaseModel):
    """更新用户模型"""
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="真实姓名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    company: Optional[str] = Field(None, max_length=100, description="公司/组织")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    avatar: Optional[str] = Field(None, max_length=500, description="头像URL")


class UserAdminUpdate(UserUpdate):
    """管理员更新用户模型"""
    role: Optional[UserRole] = Field(None, description="用户角色")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_verified: Optional[bool] = Field(None, description="是否已验证")


class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: str = Field(..., description="用户ID")
    role: UserRole = Field(..., description="用户角色")
    is_active: bool = Field(..., description="是否激活")
    is_verified: bool = Field(..., description="是否已验证邮箱")
    avatar: Optional[str] = Field(None, description="头像URL")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    
    # SSO相关字段
    external_id: Optional[str] = Field(None, description="外部系统用户ID")
    extra_metadata: Optional[dict] = Field(None, description="扩展元数据")
    
    class Config:
        from_attributes = True


class UserPublic(UserBase):
    """公开用户信息模型"""
    id: str = Field(..., description="用户ID")
    role: UserRole = Field(..., description="用户角色")
    is_active: bool = Field(..., description="是否激活")
    avatar: Optional[str] = Field(None, description="头像URL")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")
    remember: Optional[bool] = Field(False, description="记住登录状态")


class UserRegister(UserBase):
    """用户注册模型"""
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('两次输入的密码不一致')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """密码复杂度验证"""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        return v


class ChangePassword(BaseModel):
    """修改密码模型"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的新密码不一致')
        return v
    
    @validator('new_password')
    def validate_password(cls, v):
        """密码复杂度验证"""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v


class ResetPassword(BaseModel):
    """重置密码模型"""
    token: str = Field(..., description="重置密码令牌")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的新密码不一致')
        return v


class Token(BaseModel):
    """Token模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[str] = Field(None, description="用户ID")
    username: Optional[str] = Field(None, description="用户名")
    role: Optional[str] = Field(None, description="用户角色")
    external_system: Optional[str] = Field(None, description="外部系统名称")


class LoginResponse(BaseModel):
    """登录响应模型"""
    user: UserInDB = Field(..., description="用户信息")
    token: Token = Field(..., description="令牌信息")


class UserListQuery(BaseModel):
    """用户列表查询模型"""
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    role: Optional[UserRole] = Field(None, description="角色筛选")
    is_active: Optional[bool] = Field(None, description="激活状态筛选")
    search: Optional[str] = Field(None, description="搜索关键词")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="排序方向")
