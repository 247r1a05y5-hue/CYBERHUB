"""Notification schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field

from app.models.notification import NotificationType
from app.schemas.common import ORMBase


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    notification_type: NotificationType = NotificationType.system
    title: str = Field(min_length=1, max_length=255)
    message: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")


class NotificationResponse(ORMBase):
    id: uuid.UUID
    user_id: uuid.UUID
    notification_type: NotificationType
    title: str
    message: Optional[str] = None
    is_read: bool
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    created_at: datetime
    updated_at: datetime
