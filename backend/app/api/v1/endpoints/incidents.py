"""Incidents API endpoints."""
from __future__ import annotations

import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_role
from app.models.analysis_result import Severity
from app.models.incident import IncidentStatus
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentStatusTransition,
    IncidentUpdate,
    NoteCreate,
    NoteResponse,
)
from app.services.incident import IncidentService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[IncidentResponse],
    summary="List incidents with pagination and filtering",
)
async def list_incidents(
    status: Optional[IncidentStatus] = None,
    severity: Optional[Severity] = None,
    owner_id: Optional[uuid.UUID] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[IncidentResponse]:
    service = IncidentService(session)
    offset = (page - 1) * size
    items, total = await service.list_incidents(
        organization_id=current_user.organization_id,
        status=status,
        severity=severity,
        owner_id=owner_id,
        limit=size,
        offset=offset,
    )
    pages = math.ceil(total / size) if total > 0 else 1

    return PaginatedResponse(
        items=[IncidentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new security incident",
)
async def create_incident(
    incident_in: IncidentCreate,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    service = IncidentService(session)
    incident = await service.create_incident(
        organization_id=current_user.organization_id,
        incident_in=incident_in,
        actor_id=current_user.id,
    )
    return IncidentResponse.model_validate(incident)


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details with activity log",
)
async def get_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    service = IncidentService(session)
    incident = await service.get_incident(incident_id, current_user.organization_id)
    return IncidentResponse.model_validate(incident)


@router.post(
    "/{incident_id}/transition",
    response_model=IncidentResponse,
    summary="Transition incident FSM status",
)
async def transition_incident_status(
    incident_id: uuid.UUID,
    transition: IncidentStatusTransition,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    service = IncidentService(session)
    incident = await service.transition_status(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
        target_status=transition.status,
        note_content=transition.note,
        actor_id=current_user.id,
    )
    return IncidentResponse.model_validate(incident)


@router.post(
    "/{incident_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an investigation note to an incident",
)
async def add_incident_note(
    incident_id: uuid.UUID,
    note_in: NoteCreate,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> NoteResponse:
    service = IncidentService(session)
    note = await service.add_note(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
        content=note_in.content,
        author_id=current_user.id,
    )
    return NoteResponse.model_validate(note)


@router.post(
    "/{incident_id}/alerts/{alert_id}",
    response_model=IncidentResponse,
    summary="Link an alert to an incident",
)
async def link_alert_to_incident(
    incident_id: uuid.UUID,
    alert_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    service = IncidentService(session)
    incident = await service.link_alert(
        incident_id=incident_id,
        alert_id=alert_id,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
    )
    return IncidentResponse.model_validate(incident)
