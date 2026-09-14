"""Reports API endpoints."""
from __future__ import annotations

import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_role
from app.models.report import ReportFormat, ReportStatus
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.report import ReportGenerateRequest, ReportResponse
from app.services.report import ReportService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ReportResponse],
    summary="List generated reports with pagination",
)
async def list_reports(
    incident_id: Optional[uuid.UUID] = None,
    analysis_id: Optional[uuid.UUID] = None,
    status: Optional[ReportStatus] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReportResponse]:
    service = ReportService(session)
    offset = (page - 1) * size
    items, total = await service.list_reports(
        organization_id=current_user.organization_id,
        incident_id=incident_id,
        analysis_id=analysis_id,
        status=status,
        limit=size,
        offset=offset,
    )
    pages = math.ceil(total / size) if total > 0 else 1

    return PaginatedResponse(
        items=[ReportResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new security report snapshot",
)
async def generate_report(
    req: ReportGenerateRequest,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> ReportResponse:
    service = ReportService(session)
    report = await service.generate_report(
        organization_id=current_user.organization_id,
        request=req,
        actor_id=current_user.id,
    )
    return ReportResponse.model_validate(report)


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get report details",
)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReportResponse:
    service = ReportService(session)
    report = await service.get_report(report_id, current_user.organization_id)
    return ReportResponse.model_validate(report)


@router.get(
    "/{report_id}/content",
    summary="Download or view raw rendered report content",
)
async def get_report_content(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = ReportService(session)
    report = await service.get_report(report_id, current_user.organization_id)
    
    media_type = "text/html" if report.format == ReportFormat.html else "text/markdown"
    return Response(
        content=report.content or "",
        media_type=media_type,
    )
