"""Notification service."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.repositories.notification import NotificationRepository
from app.schemas.notification import NotificationCreate


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        is_read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Notification], int]:
        return await self.repo.list_for_user(
            user_id=user_id,
            is_read=is_read,
            limit=limit,
            offset=offset,
        )

    async def create_notification(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        message: Optional[str] = None,
        notification_type: NotificationType = NotificationType.system,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        return await self.repo.create(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata or {},
        )

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        return await self.repo.mark_as_read(notification_id, user_id)

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        return await self.repo.mark_all_as_read(user_id)
