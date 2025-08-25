from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import verify_token
from app.models.user import User, UserRole
from app.schemas.user import TokenData

# HTTP Bearer token scheme
security = HTTPBearer()


def get_db() -> Generator:
    """获取数据库会话"""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 验证token
        token_data = verify_token(credentials.credentials)
        if token_data.user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 从数据库获取用户信息
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """获取当前管理员用户"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限"
        )
    return current_user


def get_current_user_or_none(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """获取当前用户（可选，允许匿名访问）"""
    if credentials is None:
        return None
    
    try:
        token_data = verify_token(credentials.credentials)
        if token_data.user_id is None:
            return None
        
        user = db.query(User).filter(User.id == token_data.user_id).first()
        return user if user and user.is_active else None
    except (JWTError, HTTPException):
        return None


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, required_role: UserRole = None):
        self.required_role = required_role
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        if self.required_role and current_user.role != self.required_role:
            # 管理员可以访问所有资源
            if current_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要{self.required_role.value}权限"
                )
        return current_user


# 权限检查器实例
require_admin = PermissionChecker(UserRole.ADMIN)
require_user = PermissionChecker(UserRole.USER)


def check_datasource_access(
    datasource_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> bool:
    """检查用户是否有权限访问指定数据源"""
    # 管理员可以访问所有数据源
    if current_user.is_admin:
        return True
    
    # TODO: 实现更细粒度的数据源权限控制
    # 这里可以根据业务需求添加数据源级别的权限控制
    # 比如数据源创建者、被授权用户等
    
    return True  # 暂时允许所有用户访问


def check_user_access(
    target_user_id: str,
    current_user: User = Depends(get_current_active_user)
) -> bool:
    """检查用户是否有权限访问指定用户的信息"""
    # 用户可以访问自己的信息
    if current_user.id == target_user_id:
        return True
    
    # 管理员可以访问所有用户信息
    if current_user.is_admin:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="没有权限访问该用户信息"
    )


class RateLimiter:
    """简单的速率限制器"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        import time
        now = time.time()
        
        # 清理过期记录
        self.requests = {
            k: v for k, v in self.requests.items()
            if now - v['first_request'] < self.window_seconds
        }
        
        if key not in self.requests:
            self.requests[key] = {'count': 1, 'first_request': now}
            return True
        
        if self.requests[key]['count'] >= self.max_requests:
            return False
        
        self.requests[key]['count'] += 1
        return True


# 全局速率限制器实例
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


def check_rate_limit(
    request_key: str,
    current_user: Optional[User] = Depends(get_current_user_or_none)
):
    """检查速率限制"""
    # 使用用户ID或IP地址作为key
    key = current_user.id if current_user else request_key
    
    if not rate_limiter.is_allowed(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试"
        )
