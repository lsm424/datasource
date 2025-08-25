from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token,
    check_password_strength
)
from app.core.deps import get_current_user, get_current_active_user
from app.models.user import User, UserRole
from app.schemas.user import (
    UserLogin,
    UserRegister,
    LoginResponse,
    Token,
    UserInDB,
    ChangePassword,
    ResetPassword
)
from app.schemas.base import DataResponse, BaseResponse

router = APIRouter()


@router.post("/login", response_model=DataResponse[LoginResponse])
async def login(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """用户登录"""
    
    # 查找用户（支持用户名或邮箱登录）
    user = db.query(User).filter(
        (User.username == user_credentials.username) |
        (User.email == user_credentials.username)
    ).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
        additional_claims={
            "username": user.username,
            "role": user.role.value
        }
    )
    
    # 创建刷新令牌
    refresh_token = create_refresh_token(subject=user.id)
    
    # 更新最后登录时间
    from sqlalchemy import func
    user.last_login_at = func.now()
    db.commit()
    
    token = Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token
    )
    
    user_data = UserInDB.model_validate(user)
    
    return DataResponse(
        data=LoginResponse(user=user_data, token=token),
        message="登录成功"
    )


@router.post("/register", response_model=DataResponse[LoginResponse])
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
) -> Any:
    """用户注册"""
    
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被注册"
        )
    
    # 检查密码强度
    password_check = check_password_strength(user_data.password)
    if not password_check["is_strong"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码不符合要求: {', '.join(password_check['issues'])}"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
        phone=user_data.phone,
        company=user_data.company,
        bio=user_data.bio,
        role=UserRole.USER,  # 默认为普通用户
        is_active=True,
        is_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 创建令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=new_user.id,
        expires_delta=access_token_expires,
        additional_claims={
            "username": new_user.username,
            "role": new_user.role.value
        }
    )
    
    refresh_token = create_refresh_token(subject=new_user.id)
    
    token = Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token
    )
    
    user_response = UserInDB.model_validate(new_user)
    
    return DataResponse(
        data=LoginResponse(user=user_response, token=token),
        message="注册成功"
    )


@router.post("/refresh", response_model=DataResponse[Token])
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> Any:
    """刷新访问令牌"""
    
    try:
        # 验证刷新令牌
        token_data = verify_token(refresh_token, token_type="refresh")
        
        # 获取用户信息
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )
        
        # 创建新的访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            subject=user.id,
            expires_delta=access_token_expires,
            additional_claims={
                "username": user.username,
                "role": user.role.value
            }
        )
        
        # 创建新的刷新令牌
        new_refresh_token = create_refresh_token(subject=user.id)
        
        token = Token(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=new_refresh_token
        )
        
        return DataResponse(
            data=token,
            message="令牌刷新成功"
        )
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效"
        )


@router.post("/logout", response_model=BaseResponse)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """用户登出"""
    # TODO: 实现令牌黑名单机制
    # 目前简单返回成功，实际应该将令牌加入黑名单
    
    return BaseResponse(message="登出成功")


@router.get("/me", response_model=DataResponse[UserInDB])
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取当前用户信息"""
    
    user_data = UserInDB.model_validate(current_user)
    
    return DataResponse(
        data=user_data,
        message="获取用户信息成功"
    )


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """修改密码"""
    
    # 验证当前密码
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )
    
    # 检查新密码强度
    password_check = check_password_strength(password_data.new_password)
    if not password_check["is_strong"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"新密码不符合要求: {', '.join(password_check['issues'])}"
        )
    
    # 更新密码
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return BaseResponse(message="密码修改成功")


@router.post("/reset-password-request", response_model=BaseResponse)
async def request_password_reset(
    email: str,
    db: Session = Depends(get_db)
) -> Any:
    """请求密码重置（发送重置邮件）"""
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # 为了安全，即使用户不存在也返回成功
        return BaseResponse(message="如果邮箱存在，重置链接已发送")
    
    # TODO: 实现发送重置邮件功能
    # 这里应该生成重置令牌并发送邮件
    
    return BaseResponse(message="重置链接已发送到您的邮箱")


@router.post("/reset-password", response_model=BaseResponse)
async def reset_password(
    reset_data: ResetPassword,
    db: Session = Depends(get_db)
) -> Any:
    """重置密码"""
    
    try:
        # 验证重置令牌
        from app.core.security import verify_password_reset_token
        email = verify_password_reset_token(reset_data.token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="重置令牌无效或已过期"
            )
        
        # 查找用户
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 检查新密码强度
        password_check = check_password_strength(reset_data.new_password)
        if not password_check["is_strong"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"新密码不符合要求: {', '.join(password_check['issues'])}"
            )
        
        # 更新密码
        user.hashed_password = get_password_hash(reset_data.new_password)
        db.commit()
        
        return BaseResponse(message="密码重置成功")
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码重置失败"
        )
