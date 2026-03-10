from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_current_admin_user
from app.models.user import User, UserRole
from app.models.role import Role
from app.schemas.user import (
    UserPublic,
    UserInDB,
    UserUpdate,
    UserAdminUpdate,
    UserCreate,
    UserListQuery
)
from app.schemas.base import DataResponse, ListResponse, BaseResponse
from app.core.security import get_password_hash

router = APIRouter()


@router.get("/", response_model=ListResponse[UserPublic])
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: UserRole = Query(None),
    is_active: bool = Query(None),
    search: str = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取用户列表（仅管理员）"""
    
    query = db.query(User)
    
    # 角色筛选（系统角色 admin/user）
    if role:
        query = query.filter(User.role == role)
    
    # 活跃状态筛选
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # 搜索
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.username.like(search_pattern)) |
            (User.name.like(search_pattern)) |
            (User.email.like(search_pattern))
        )
    
    # 计算总数
    total = query.count()
    
    # 分页
    users = query.offset((page - 1) * limit).limit(limit).all()
    
    # 预取所有角色，构建映射
    roles = {r.id: r for r in db.query(Role).all()}
    
    # 转换为响应模型，并附加角色名称
    user_list = []
    for user in users:
        data = UserPublic.model_validate(user).model_dump(by_alias=True)
        if user.role_id and user.role_id in roles:
            data["roleName"] = roles[user.role_id].name
            data["roleCode"] = roles[user.role_id].code
        user_list.append(data)
    
    return ListResponse.create(
        data=user_list,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/me", response_model=DataResponse[UserInDB])
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取当前用户信息"""
    user_data = UserInDB.model_validate(current_user)
    
    return DataResponse(
        data=user_data,
        message="获取用户信息成功"
    )


@router.put("/me", response_model=DataResponse[UserInDB])
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """更新当前用户信息"""
    
    # 检查邮箱是否已被其他用户使用
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被其他用户使用"
            )
    
    # 更新用户信息
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    user_data = UserInDB.model_validate(current_user)
    
    return DataResponse(
        data=user_data,
        message="用户信息更新成功"
    )


@router.get("/{user_id}", response_model=DataResponse[UserPublic])
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """根据ID获取用户信息（仅管理员）"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    roles = {r.id: r for r in db.query(Role).all()}
    data = UserPublic.model_validate(user).model_dump(by_alias=True)
    if user.role_id and user.role_id in roles:
        data["roleName"] = roles[user.role_id].name
        data["roleCode"] = roles[user.role_id].code
    
    return DataResponse(
        data=data,
        message="获取用户信息成功"
    )


@router.post("/", response_model=DataResponse[UserPublic])
async def create_user(
    user_create: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """创建用户（仅管理员）"""
    
    logging.info(f"Creating user: {user_create.username} ({user_create.email})")
    
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_create.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_create.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被注册"
        )
    
    # 创建用户
    hashed_password = get_password_hash(user_create.password)
    user_data = user_create.model_dump(exclude={"password"})
    user_data["hashed_password"] = hashed_password
    
    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    roles = {r.id: r for r in db.query(Role).all()}
    data = UserPublic.model_validate(new_user).model_dump(by_alias=True)
    if new_user.role_id and new_user.role_id in roles:
        data["roleName"] = roles[new_user.role_id].name
        data["roleCode"] = roles[new_user.role_id].code
    
    return DataResponse(
        data=data,
        message="用户创建成功"
    )


@router.put("/{user_id}", response_model=DataResponse[UserPublic])
async def update_user(
    user_id: str,
    user_update: UserAdminUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """更新用户信息（仅管理员）"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 检查邮箱是否已被其他用户使用
    if user_update.email and user_update.email != user.email:
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被其他用户使用"
            )
    
    # 更新用户信息
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    roles = {r.id: r for r in db.query(Role).all()}
    data = UserPublic.model_validate(user).model_dump(by_alias=True)
    if user.role_id and user.role_id in roles:
        data["roleName"] = roles[user.role_id].name
        data["roleCode"] = roles[user.role_id].code
    
    return DataResponse(
        data=data,
        message="用户信息更新成功"
    )


@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """删除用户（仅管理员）"""
    
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    db.delete(user)
    db.commit()
    
    return BaseResponse(message="用户删除成功")
