"""
SSO单点登录API接口
提供外部系统集成和token交换功能
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.sso import (
    SSOAuthenticationHandler,
    JWTSharedSSOProvider,
    APIKeyManager,
    ExternalTokenValidator,
    SSOUserManager,
    get_sso_user,
    get_sso_user_shared_jwt,
    get_sso_user_api_key,
    get_current_user_mixed
)
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.schemas.base import DataResponse, BaseResponse
from app.schemas.user import UserInDB


router = APIRouter()


@router.post("/token-exchange", response_model=DataResponse[dict])
async def exchange_external_token(
    request: Request,
    external_token: str,
    system_name: str = "external",
    db: Session = Depends(get_db)
) -> Any:
    """外部系统Token交换 - 将外部系统的token转换为本系统token"""
    
    try:
        # 创建外部token验证器
        async with ExternalTokenValidator() as validator:
            # 验证外部token
            user_data = await validator.validate_external_token(external_token, system_name)
            
            # 获取或创建SSO用户
            user_manager = SSOUserManager(db)
            user = user_manager.get_or_create_sso_user(user_data)
            
            # 生成本系统的JWT token
            jwt_provider = JWTSharedSSOProvider()
            access_token = jwt_provider.create_compatible_token({
                "user_id": user.id,
                "username": user.username,
                "role": user.role.value,
                "email": user.email,
                "name": user.name
            })
            
            return DataResponse(
                data={
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "name": user.name,
                        "email": user.email,
                        "role": user.role.value
                    },
                    "sso_info": {
                        "source_system": system_name,
                        "external_user_id": user_data.get("user_id"),
                        "created_via_sso": True
                    }
                },
                message="Token交换成功"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token交换失败: {str(e)}"
        )


@router.post("/validate-shared-token", response_model=DataResponse[dict])
async def validate_shared_token(
    shared_token: str,
    db: Session = Depends(get_db)
) -> Any:
    """验证共享JWT Token"""
    
    try:
        jwt_provider = JWTSharedSSOProvider()
        token_data = jwt_provider.verify_shared_token(shared_token)
        
        # 获取或创建用户
        user_manager = SSOUserManager(db)
        user = user_manager.get_or_create_sso_user({
            "user_id": token_data.user_id,
            "username": token_data.username,
            "role": token_data.role,
            "system": getattr(token_data, 'external_system', 'shared')
        })
        
        return DataResponse(
            data={
                "valid": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role.value,
                    "is_active": user.is_active
                },
                "token_info": {
                    "user_id": token_data.user_id,
                    "username": token_data.username,
                    "role": token_data.role,
                    "source_system": getattr(token_data, 'external_system', 'shared')
                }
            },
            message="Token验证成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token验证失败: {str(e)}"
        )


@router.post("/generate-api-key", response_model=DataResponse[dict])
async def generate_api_key(
    target_user_id: str,
    system_name: str = "external",
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """为外部系统生成API Key (管理员专用)"""
    
    try:
        api_key = APIKeyManager.generate_api_key(target_user_id, system_name)
        
        return DataResponse(
            data={
                "api_key": api_key,
                "user_id": target_user_id,
                "system_name": system_name,
                "expires_in_days": 365,
                "usage": "将此API Key放在HTTP请求头中: Authorization: Bearer <api_key>"
            },
            message="API Key生成成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API Key生成失败: {str(e)}"
        )


@router.post("/validate-api-key", response_model=DataResponse[dict])
async def validate_api_key(
    api_key: str,
    db: Session = Depends(get_db)
) -> Any:
    """验证API Key"""
    
    try:
        api_data = APIKeyManager.verify_api_key(api_key)
        
        # 查找用户
        user = db.query(User).filter(User.id == api_data["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key对应的用户不存在"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账户已被禁用"
            )
        
        return DataResponse(
            data={
                "valid": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role.value,
                    "is_active": user.is_active
                },
                "api_key_info": {
                    "system": api_data["system"],
                    "issued_at": api_data["issued_at"].isoformat(),
                    "expires_at": api_data["expires_at"].isoformat()
                }
            },
            message="API Key验证成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API Key验证失败: {str(e)}"
        )


@router.get("/me", response_model=DataResponse[UserInDB])
async def get_sso_current_user(
    current_user: User = Depends(get_sso_user)
) -> Any:
    """获取当前SSO用户信息"""
    
    user_data = UserInDB.model_validate(current_user)
    
    return DataResponse(
        data=user_data,
        message="获取用户信息成功"
    )


@router.get("/me/mixed", response_model=DataResponse[UserInDB])
async def get_mixed_current_user(
    current_user: User = Depends(get_current_user_mixed)
) -> Any:
    """获取当前用户信息 (支持标准认证和SSO混合)"""
    
    user_data = UserInDB.model_validate(current_user)
    
    # 添加SSO相关信息
    sso_info = {}
    if current_user.external_id:
        sso_info = {
            "is_sso_user": True,
            "external_id": current_user.external_id,
            "sso_system": current_user.extra_metadata.get("sso_system") if current_user.extra_metadata else None,
            "created_via_sso": current_user.extra_metadata.get("created_via_sso", False) if current_user.extra_metadata else False
        }
    else:
        sso_info = {
            "is_sso_user": False
        }
    
    return DataResponse(
        data={
            **user_data.model_dump(),
            "sso_info": sso_info
        },
        message="获取用户信息成功"
    )


@router.get("/systems", response_model=DataResponse[dict])
async def get_supported_systems(
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """获取支持的外部系统列表 (管理员专用)"""
    
    from app.core.sso import SSOConfig
    
    return DataResponse(
        data={
            "external_systems": list(SSOConfig.EXTERNAL_SYSTEM_ENDPOINTS.keys()),
            "oauth2_providers": list(SSOConfig.OAUTH2_PROVIDERS.keys()),
            "supported_auth_types": [
                "shared_jwt",
                "external_token",
                "api_key",
                "oauth2"
            ],
            "endpoints": {
                "token_exchange": "/api/v1/sso/token-exchange",
                "validate_shared_token": "/api/v1/sso/validate-shared-token",
                "validate_api_key": "/api/v1/sso/validate-api-key",
                "current_user": "/api/v1/sso/me"
            }
        },
        message="获取支持的系统列表成功"
    )


@router.post("/test-integration", response_model=DataResponse[dict])
async def test_sso_integration(
    test_token: str,
    auth_type: str = "shared_jwt",
    system_name: str = "test_system",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """SSO集成测试接口 (管理员专用)"""
    
    results = {
        "auth_type": auth_type,
        "system_name": system_name,
        "test_results": {}
    }
    
    try:
        if auth_type == "shared_jwt":
            jwt_provider = JWTSharedSSOProvider()
            token_data = jwt_provider.verify_shared_token(test_token)
            results["test_results"]["token_validation"] = {
                "success": True,
                "user_id": token_data.user_id,
                "username": token_data.username,
                "role": token_data.role
            }
            
        elif auth_type == "api_key":
            api_data = APIKeyManager.verify_api_key(test_token)
            results["test_results"]["api_key_validation"] = {
                "success": True,
                "user_id": api_data["user_id"],
                "system": api_data["system"],
                "expires_at": api_data["expires_at"].isoformat()
            }
            
        elif auth_type == "external_token":
            async with ExternalTokenValidator() as validator:
                user_data = await validator.validate_external_token(test_token, system_name)
                results["test_results"]["external_validation"] = {
                    "success": True,
                    "user_data": user_data
                }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的认证类型: {auth_type}"
            )
        
        # 测试用户获取/创建
        user_manager = SSOUserManager(db)
        if auth_type == "shared_jwt":
            sso_data = {
                "user_id": token_data.user_id,
                "username": token_data.username,
                "role": token_data.role,
                "system": system_name
            }
            user = user_manager.get_or_create_sso_user(sso_data)
            results["test_results"]["user_management"] = {
                "success": True,
                "user_id": user.id,
                "username": user.username,
                "created_new": user.external_id is not None
            }
        
        results["overall_status"] = "success"
        
        return DataResponse(
            data=results,
            message="SSO集成测试完成"
        )
        
    except Exception as e:
        results["test_results"]["error"] = str(e)
        results["overall_status"] = "failed"
        
        return DataResponse(
            data=results,
            message=f"SSO集成测试失败: {str(e)}"
        )
