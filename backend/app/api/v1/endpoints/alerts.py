"""Alerts API endpoints."""
from __future__ import annotations

import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_role
from app.models.alert import AlertStatus
from app.models.analysis_result import Severity
from app.models.user import User, UserRole
from app.schemas.alert import AlertCreate, AlertResponse, AlertUpdate
from app.schemas.common import PaginatedResponse
from app.services.alert import AlertService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[AlertResponse],
    summary="List alerts with pagination and filtering",
)
async def list_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[Severity] = None,
    assigned_to_id: Optional[uuid.UUID] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AlertResponse]:
    service = AlertService(session)
    offset = (page - 1) * size
    items, total = await service.list_alerts(
        organization_id=current_user.organization_id,
        status=status,
        severity=severity,
        assigned_to_id=assigned_to_id,
        limit=size,
        offset=offset,
    )
    pages = math.ceil(total / size) if total > 0 else 1

    return PaginatedResponse(
        items=[AlertResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create alert manually",
)
async def create_alert(
    alert_in: AlertCreate,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> AlertResponse:
    service = AlertService(session)
    alert = await service.create_alert(
        organization_id=current_user.organization_id,
        alert_in=alert_in,
        actor_id=current_user.id,
    )
    return AlertResponse.model_validate(alert)


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert details",
)
async def get_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AlertResponse:
    service = AlertService(session)
    alert = await service.get_alert(alert_id, current_user.organization_id)
    return AlertResponse.model_validate(alert)


@router.patch(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Update alert status, assignment, or metadata",
)
async def update_alert(
    alert_id: uuid.UUID,
    alert_in: AlertUpdate,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> AlertResponse:
    service = AlertService(session)
    alert = await service.update_alert(
        alert_id=alert_id,
        organization_id=current_user.organization_id,
        alert_in=alert_in,
        actor_id=current_user.id,
    )
    return AlertResponse.model_validate(alert)
