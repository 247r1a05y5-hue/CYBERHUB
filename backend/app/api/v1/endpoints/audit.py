"""Audit logs API endpoints."""
from __future__ import annotations

import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_role
from app.models.audit_log import AuditAction
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="List immutable audit trail events (Analyst/Admin)",
)
async def list_audit_logs(
    target_type: Optional[str] = None,
    action: Optional[AuditAction] = None,
    user_id: Optional[uuid.UUID] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AuditLogResponse]:
    repo = AuditLogRepository(session)
    offset = (page - 1) * size
    items, total = await repo.list_by_org(
        organization_id=current_user.organization_id,
        target_type=target_type,
        action=action,
        user_id=user_id,
        limit=size,
        offset=offset,
    )
    pages = math.ceil(total / size) if total > 0 else 1

    return PaginatedResponse(
        items=[
            AuditLogResponse(
                id=a.id,
                org_id=a.organization_id,
                user_id=a.user_id,
                action=a.action,
                target_type=a.target_type,
                target_id=a.target_id,
                details=a.details,
                ip_address=a.ip_address,
                user_agent=a.user_agent,
                created_at=a.created_at,
            )
            for a in items
        ],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )
