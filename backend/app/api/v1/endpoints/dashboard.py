"""Dashboard API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.dashboard import DashboardMetrics
from app.services.dashboard import DashboardService

router = APIRouter()


@router.get(
    "/metrics",
    response_model=DashboardMetrics,
    summary="Get aggregated operational metrics and trend data",
)
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardMetrics:
    service = DashboardService(session)
    return await service.get_metrics(current_user.organization_id)
