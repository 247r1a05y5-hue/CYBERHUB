"""Users management API endpoints."""
from __future__ import annotations

import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_role
from app.core.security import hash_password
from app.models.audit_log import AuditAction
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.audit import AuditService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List users in organization (Admin only)",
)
async def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    repo = UserRepository(session)
    offset = (page - 1) * size
    items, total = await repo.list_by_org(
        organization_id=current_user.organization_id,
        limit=size,
        offset=offset,
    )
    pages = math.ceil(total / size) if total > 0 else 1

    return PaginatedResponse(
        items=[
            UserResponse(
                id=u.id,
                org_id=u.organization_id,
                email=u.email,
                role=u.role,
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in items
        ],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user in the organization (Admin only)",
)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(session)
    audit = AuditService(session)

    existing = await repo.get_by_email_and_org(user_in.email, current_user.organization_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists in organization",
        )

    pwd_hash = hash_password(user_in.password)
    user = await repo.create(
        organization_id=current_user.organization_id,
        email=user_in.email.lower().strip(),
        password_hash=pwd_hash,
        role=user_in.role,
        is_active=user_in.is_active,
    )

    await audit.log(
        organization_id=current_user.organization_id,
        action=AuditAction.create,
        target_type="user",
        target_id=str(user.id),
        user_id=current_user.id,
        details={"email": user.email, "role": user.role.value},
    )

    return UserResponse(
        id=user.id,
        org_id=user.organization_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user role or active status (Admin only)",
)
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(session)
    audit = AuditService(session)

    user = await repo.get_by_id_and_org(user_id, current_user.organization_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    updates = user_in.model_dump(exclude_unset=True)
    if "password" in updates and updates["password"]:
        updates["password_hash"] = hash_password(updates.pop("password"))
    elif "password" in updates:
        updates.pop("password")

    for k, v in updates.items():
        setattr(user, k, v)

    await repo.save(user)

    await audit.log(
        organization_id=current_user.organization_id,
        action=AuditAction.update,
        target_type="user",
        target_id=str(user.id),
        user_id=current_user.id,
        details={"updated_fields": list(updates.keys())},
    )

    return UserResponse(
        id=user.id,
        org_id=user.organization_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
