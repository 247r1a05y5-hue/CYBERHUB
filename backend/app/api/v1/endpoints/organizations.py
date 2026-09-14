"""Organizations API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_role
from app.models.audit_log import AuditAction
from app.models.user import User, UserRole
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import (
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.audit import AuditService

router = APIRouter()


@router.get(
    "/me",
    response_model=OrganizationResponse,
    summary="Get details for current organization",
)
async def get_my_organization(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    repo = OrganizationRepository(session)
    org = await repo.get_by_id(current_user.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return OrganizationResponse.model_validate(org)


@router.patch(
    "/me",
    response_model=OrganizationResponse,
    summary="Update organization name (Admin only)",
)
async def update_my_organization(
    org_in: OrganizationUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    repo = OrganizationRepository(session)
    audit = AuditService(session)

    org = await repo.get_by_id(current_user.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if org_in.name:
        org.name = org_in.name
        await repo.save(org)

        await audit.log(
            organization_id=org.id,
            action=AuditAction.update,
            target_type="organization",
            target_id=str(org.id),
            user_id=current_user.id,
            details={"name": org.name},
        )

    return OrganizationResponse.model_validate(org)
