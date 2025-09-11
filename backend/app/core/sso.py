"""
单点登录(SSO)集成模块
提供多种SSO认证方案，支持外部系统无缝接入
"""

import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core.config import settings
from app.core.security import verify_token, create_access_token
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import TokenData, UserCreate


class SSOConfig:
    """SSO配置类"""
    
    # JWT共享配置
    SHARED_JWT_SECRET = settings.SECRET_KEY
    SHARED_JWT_ALGORITHM = "HS256"
    
    # 外部系统验证配置
    EXTERNAL_SYSTEM_ENDPOINTS = {
        "system_a": "http://external-system-a.com/api/v1/auth/validate",
        "system_b": "http://external-system-b.com/api/v1/user/verify",
        # 添加更多外部系统...
    }
    
    # API Key配置
    API_KEY_HEADER = "X-API-Key"
    API_KEY_EXPIRY_DAYS = 365
    
    # OAuth2/OIDC配置
    OAUTH2_PROVIDERS = {
        "microsoft": {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "authorization_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/v1.0/me"
        },
        "google": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo"
        }
    }


class JWTSharedSSOProvider:
    """JWT共享SSO提供器 - 与外部系统共享相同的JWT密钥和格式"""
    
    def __init__(self, shared_secret: str = None, algorithm: str = "HS256"):
        self.secret = shared_secret or SSOConfig.SHARED_JWT_SECRET
        self.algorithm = algorithm
    
    def verify_shared_token(self, token: str) -> TokenData:
        """验证来自外部系统的共享JWT Token"""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            
            # 检查必要的字段
            user_id = payload.get("sub")
            username = payload.get("username")
            role = payload.get("role", "user")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token中缺少用户ID"
                )
            
            return TokenData(
                user_id=user_id,
                username=username,
                role=role,
                external_system=payload.get("system", "unknown")
            )
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token验证失败: {str(e)}"
            )
    
    def create_compatible_token(self, user_data: Dict[str, Any]) -> str:
        """创建与外部系统兼容的JWT Token"""
        additional_claims = {
            "username": user_data.get("username"),
            "role": user_data.get("role", "user"),
            "system": "data-browser",
            "email": user_data.get("email"),
            "name": user_data.get("name")
        }
        
        return create_access_token(
            subject=user_data["user_id"],
            additional_claims=additional_claims
        )


class ExternalTokenValidator:
    """外部Token验证器 - 调用外部系统API验证token"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def validate_external_token(self, token: str, system_name: str) -> Dict[str, Any]:
        """调用外部系统API验证token"""
        endpoint = SSOConfig.EXTERNAL_SYSTEM_ENDPOINTS.get(system_name)
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的外部系统: {system_name}"
            )
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = await self.client.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "user_id": user_data.get("id") or user_data.get("user_id"),
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "name": user_data.get("name"),
                    "role": user_data.get("role", "user"),
                    "system": system_name
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="外部系统token验证失败"
                )
                
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="外部系统验证超时"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"外部系统验证服务不可用: {str(e)}"
            )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


class APIKeyManager:
    """API Key管理器 - 为外部系统生成和验证API Key"""
    
    @staticmethod
    def generate_api_key(user_id: str, system_name: str = "external") -> str:
        """生成API Key"""
        expiry = datetime.utcnow() + timedelta(days=SSOConfig.API_KEY_EXPIRY_DAYS)
        
        payload = {
            "sub": user_id,
            "system": system_name,
            "type": "api_key",
            "exp": expiry.timestamp(),
            "iat": datetime.utcnow().timestamp()
        }
        
        return jwt.encode(payload, SSOConfig.SHARED_JWT_SECRET, algorithm="HS256")
    
    @staticmethod
    def verify_api_key(api_key: str) -> Dict[str, Any]:
        """验证API Key"""
        try:
            payload = jwt.decode(api_key, SSOConfig.SHARED_JWT_SECRET, algorithms=["HS256"])
            
            if payload.get("type") != "api_key":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的API Key类型"
                )
            
            return {
                "user_id": payload.get("sub"),
                "system": payload.get("system", "external"),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0))
            }
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key验证失败"
            )


class SSOUserManager:
    """SSO用户管理器 - 处理来自外部系统的用户信息"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_sso_user(self, sso_data: Dict[str, Any]) -> User:
        """获取或创建SSO用户"""
        external_user_id = sso_data.get("user_id")
        system_name = sso_data.get("system", "external")
        
        # 构造唯一的外部用户标识
        external_identifier = f"{system_name}:{external_user_id}"
        
        # 查找现有用户
        user = self.db.query(User).filter(
            User.external_id == external_identifier
        ).first()
        
        if user:
            # 更新用户信息
            if sso_data.get("email") and user.email != sso_data["email"]:
                user.email = sso_data["email"]
            if sso_data.get("name") and user.name != sso_data["name"]:
                user.name = sso_data["name"]
            
            self.db.commit()
            self.db.refresh(user)
            return user
        
        # 创建新用户
        username = sso_data.get("username") or f"{system_name}_{external_user_id}"
        
        # 确保用户名唯一
        counter = 1
        original_username = username
        while self.db.query(User).filter(User.username == username).first():
            username = f"{original_username}_{counter}"
            counter += 1
        
        new_user = User(
            username=username,
            name=sso_data.get("name", username),
            email=sso_data.get("email"),
            role=UserRole.USER if sso_data.get("role") == "user" else UserRole.ADMIN,
            is_active=True,
            external_id=external_identifier,
            hashed_password="",  # SSO用户不需要本地密码
            extra_metadata={
                "sso_system": system_name,
                "created_via_sso": True,
                "original_user_id": external_user_id
            }
        )
        
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        return new_user


class SSOAuthenticationHandler:
    """SSO认证处理器 - 统一的SSO认证入口"""
    
    def __init__(self):
        self.jwt_provider = JWTSharedSSOProvider()
        self.external_validator = ExternalTokenValidator()
    
    async def authenticate_sso_user(
        self, 
        credentials: HTTPAuthorizationCredentials,
        db: Session,
        auth_type: str = "auto"
    ) -> User:
        """SSO用户认证统一入口"""
        token = credentials.credentials
        user_manager = SSOUserManager(db)
        
        try:
            if auth_type == "shared_jwt" or auth_type == "auto":
                # 尝试JWT共享验证
                try:
                    token_data = self.jwt_provider.verify_shared_token(token)
                    sso_data = {
                        "user_id": token_data.user_id,
                        "username": token_data.username,
                        "role": token_data.role,
                        "system": getattr(token_data, 'external_system', 'shared')
                    }
                    return user_manager.get_or_create_sso_user(sso_data)
                except HTTPException:
                    if auth_type == "shared_jwt":
                        raise
                    # 如果是auto模式，继续尝试其他方式
            
            if auth_type == "api_key" or auth_type == "auto":
                # 尝试API Key验证
                try:
                    api_data = APIKeyManager.verify_api_key(token)
                    # 根据API Key中的user_id查找用户
                    user = db.query(User).filter(User.id == api_data["user_id"]).first()
                    if user and user.is_active:
                        return user
                except HTTPException:
                    if auth_type == "api_key":
                        raise
            
            # 如果都失败了，回退到标准验证
            if auth_type == "auto":
                token_data = verify_token(token)
                user = db.query(User).filter(User.id == token_data.user_id).first()
                if user and user.is_active:
                    return user
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无法验证SSO凭据"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"SSO认证失败: {str(e)}"
            )


# SSO认证依赖项
sso_security = HTTPBearer()
sso_handler = SSOAuthenticationHandler()


async def get_sso_user(
    credentials: HTTPAuthorizationCredentials = Depends(sso_security),
    db: Session = Depends(get_db),
    auth_type: str = "auto"
) -> User:
    """获取SSO认证用户的依赖项"""
    return await sso_handler.authenticate_sso_user(credentials, db, auth_type)


async def get_sso_user_shared_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(sso_security),
    db: Session = Depends(get_db)
) -> User:
    """使用JWT共享方式获取SSO用户"""
    return await sso_handler.authenticate_sso_user(credentials, db, "shared_jwt")


async def get_sso_user_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(sso_security),
    db: Session = Depends(get_db)
) -> User:
    """使用API Key方式获取SSO用户"""
    return await sso_handler.authenticate_sso_user(credentials, db, "api_key")


def get_current_user_or_sso(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(sso_security)
) -> Optional[User]:
    """获取当前用户（支持标准认证和SSO）"""
    if credentials is None:
        return None
    
    try:
        # 首先尝试标准认证
        token_data = verify_token(credentials.credentials)
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user and user.is_active:
            return user
    except:
        pass
    
    try:
        # 尝试SSO认证
        import asyncio
        return asyncio.run(sso_handler.authenticate_sso_user(credentials, db))
    except:
        pass
    
    return None


# 兼容性函数 - 支持标准认证和SSO的混合模式
def get_current_user_mixed(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> User:
    """混合认证模式 - 支持标准用户和SSO用户"""
    try:
        # 标准认证
        token_data = verify_token(credentials.credentials)
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user and user.is_active:
            return user
    except:
        pass
    
    # SSO认证
    import asyncio
    try:
        return asyncio.run(sso_handler.authenticate_sso_user(credentials, db))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证用户凭据"
        )
