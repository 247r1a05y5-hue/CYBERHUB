"""Timeline Service — Immutable Chronological Investigation Audit & Event Trail."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.intelligence import TimelineEvent

logger = logging.getLogger(__name__)


class TimelineService:
    """Records and queries immutable investigation timeline events."""

    @classmethod
    async def record_event(
        cls,
        db: AsyncSession,
        case_id: uuid.UUID,
        event_type: str,
        title: str,
        description: str,
        actor_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TimelineEvent:
        """Append an immutable timeline event to the investigation history."""
        # Sanitize metadata to ensure no raw bytes or credentials
        clean_meta = {}
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, bytes):
                    continue
                if any(secret_term in k.lower() for secret_term in ["token", "secret", "key", "password"]):
                    clean_meta[k] = "[REDACTED]"
                else:
                    clean_meta[k] = v

        event = TimelineEvent(
            case_id=case_id,
            event_type=event_type,
            title=title,
            description=description,
            actor_id=actor_id,
            metadata_json=clean_meta,
        )
        db.add(event)
        await db.flush()
        return event

    @classmethod
    async def get_timeline(
        cls,
        db: AsyncSession,
        case_id: uuid.UUID,
        ascending: bool = True,
    ) -> list[dict[str, Any]]:
        """Retrieve chronological timeline events for an investigation."""
        stmt = select(TimelineEvent).where(TimelineEvent.case_id == case_id)
        if ascending:
            stmt = stmt.order_by(TimelineEvent.created_at.asc())
        else:
            stmt = stmt.order_by(TimelineEvent.created_at.desc())

        res = await db.execute(stmt)
        events = res.scalars().all()

        return [
            {
                "id": str(e.id),
                "case_id": str(e.case_id),
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "timestamp": e.created_at.isoformat() if e.created_at else datetime.now(timezone.utc).isoformat(),
                "metadata": e.metadata_json,
            }
            for e in events
        ]


timeline_service = TimelineService()
