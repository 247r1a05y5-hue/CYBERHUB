"""Notifications API endpoints."""
from __future__ import annotations

import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.notification import NotificationResponse
from app.services.notification import NotificationService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
    summary="List notifications for current user",
)
async def list_notifications(
    is_read: Optional[bool] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[NotificationResponse]:
    service = NotificationService(session)
    offset = (page - 1) * size
    items, total = await service.list_notifications(
        user_id=current_user.id,
        is_read=is_read,
        limit=size,
        offset=offset,
    )
    pages = math.ceil(total / size) if total > 0 else 1

    return PaginatedResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=MessageResponse,
    summary="Mark a notification as read",
)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    service = NotificationService(session)
    await service.mark_read(notification_id, current_user.id)
    return MessageResponse(message="Notification marked as read")


@router.post(
    "/read-all",
    response_model=MessageResponse,
    summary="Mark all notifications as read for current user",
)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    service = NotificationService(session)
    count = await service.mark_all_read(current_user.id)
    return MessageResponse(message=f"Marked {count} notifications as read")
