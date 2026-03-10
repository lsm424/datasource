from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.models.role import Role, RoleDatasetPermission
from app.schemas.role import RoleCreate, RoleUpdate, RolePublic, RoleWithDatasets
from app.schemas.base import DataResponse, ListResponse, BaseResponse

router = APIRouter()


@router.get("", response_model=ListResponse[RolePublic])
async def list_roles(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """获取角色列表（仅管理员）"""
    roles = db.query(Role).order_by(Role.created_at.asc()).all()
    data = [RolePublic.model_validate(r).model_dump(by_alias=True) for r in roles]
    return ListResponse.create(data=data, total=len(data), page=1, limit=len(data) or 1)


@router.post("", response_model=DataResponse[RolePublic])
async def create_role(
    role_create: RoleCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """创建角色（仅管理员）"""
    if db.query(Role).filter(Role.code == role_create.code).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="角色编码已存在",
        )
    if db.query(Role).filter(Role.name == role_create.name).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="角色名称已存在",
        )
    role = Role(**role_create.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    data = RolePublic.model_validate(role)
    return DataResponse(data=data, message="角色创建成功")


@router.put("/{role_id}", response_model=DataResponse[RolePublic])
async def update_role(
    role_id: str,
    role_update: RoleUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """更新角色（仅管理员）"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    if role.built_in and role_update.name is not None and role_update.name != role.name:
        # 内置角色允许改描述，不允许改名称
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="内置角色名称不可修改")

    update_data = role_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    data = RolePublic.model_validate(role)
    return DataResponse(data=data, message="角色更新成功")


@router.delete("/{role_id}", response_model=BaseResponse)
async def delete_role(
    role_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """删除角色（仅管理员，内置角色禁止删除）"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    if role.built_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="内置角色不可删除")

    # 检查是否有用户正在使用该角色
    from app.models.user import User as UserModel

    in_use = db.query(UserModel).filter(UserModel.role_id == role_id).first()
    if in_use:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仍有用户绑定该角色，无法删除")

    db.query(RoleDatasetPermission).filter(RoleDatasetPermission.role_id == role_id).delete()
    db.delete(role)
    db.commit()
    return BaseResponse(message="角色删除成功")


@router.get("/{role_id}/datasets", response_model=DataResponse[RoleWithDatasets])
async def get_role_datasets(
    role_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """获取角色绑定的数据源ID列表"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    perms = db.query(RoleDatasetPermission).filter(RoleDatasetPermission.role_id == role_id).all()
    dataset_ids = [p.datasource_id for p in perms]
    data = RoleWithDatasets.model_validate(
        {
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "built_in": role.built_in,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "dataset_ids": dataset_ids,
        }
    )
    return DataResponse(data=data, message="获取角色数据权限成功")


@router.put("/{role_id}/datasets", response_model=BaseResponse)
async def update_role_datasets(
    role_id: str,
    dataset_ids: List[str],
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """更新角色绑定的数据源ID列表（仅管理员）"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")

    # 先删除旧的，再插入新的
    db.query(RoleDatasetPermission).filter(RoleDatasetPermission.role_id == role_id).delete()

    for ds_id in set(dataset_ids):
        perm = RoleDatasetPermission(role_id=role_id, datasource_id=ds_id)
        db.add(perm)

    db.commit()
    return BaseResponse(message="角色数据权限更新成功")

