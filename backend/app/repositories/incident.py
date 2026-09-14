"""Incident, Note, and IncidentAlert repositories."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis_result import Severity
from app.models.incident import Incident, IncidentStatus
from app.models.incident_alert import IncidentAlert
from app.models.note import Note
from app.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    async def get_with_details(
        self, incident_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Optional[Incident]:
        stmt = (
            select(Incident)
            .options(
                selectinload(Incident.owner),
                selectinload(Incident.notes).selectinload(Note.author),
                selectinload(Incident.alert_links).selectinload(IncidentAlert.alert),
            )
            .where(
                Incident.id == incident_id,
                Incident.organization_id == organization_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: uuid.UUID,
        status: Optional[IncidentStatus] = None,
        severity: Optional[Severity] = None,
        owner_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Incident], int]:
        stmt = select(Incident).where(Incident.organization_id == organization_id)
        count_stmt = select(func.count(Incident.id)).where(Incident.organization_id == organization_id)

        if status is not None:
            stmt = stmt.where(Incident.status == status)
            count_stmt = count_stmt.where(Incident.status == status)
        if severity is not None:
            stmt = stmt.where(Incident.severity == severity)
            count_stmt = count_stmt.where(Incident.severity == severity)
        if owner_id is not None:
            stmt = stmt.where(Incident.owner_id == owner_id)
            count_stmt = count_stmt.where(Incident.owner_id == owner_id)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            stmt.options(selectinload(Incident.owner), selectinload(Incident.notes))
            .order_by(desc(Incident.updated_at))
            .offset(offset)
            .limit(limit)
        )
        items_res = await self.session.execute(stmt)
        return list(items_res.scalars().all()), total

    async def update_incident(
        self,
        incident_id: uuid.UUID,
        organization_id: uuid.UUID,
        **updates: Any,
    ) -> Optional[Incident]:
        updates["updated_at"] = datetime.now(timezone.utc)
        stmt = (
            update(Incident)
            .where(Incident.id == incident_id, Incident.organization_id == organization_id)
            .values(**updates)
            .returning(Incident)
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.scalar_one_or_none()


class NoteRepository(BaseRepository[Note]):
    model = Note

    async def create_note(
        self, incident_id: uuid.UUID, author_id: uuid.UUID, content: str
    ) -> Note:
        note = Note(incident_id=incident_id, author_id=author_id, content=content)
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def list_by_incident(self, incident_id: uuid.UUID) -> List[Note]:
        stmt = (
            select(Note)
            .options(selectinload(Note.author))
            .where(Note.incident_id == incident_id)
            .order_by(Note.created_at)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class IncidentAlertRepository(BaseRepository[IncidentAlert]):
    model = IncidentAlert

    async def link(self, incident_id: uuid.UUID, alert_id: uuid.UUID) -> IncidentAlert:
        link = IncidentAlert(incident_id=incident_id, alert_id=alert_id)
        self.session.add(link)
        await self.session.flush()
        return link

    async def is_linked(self, incident_id: uuid.UUID, alert_id: uuid.UUID) -> bool:
        stmt = select(IncidentAlert).where(
            IncidentAlert.incident_id == incident_id,
            IncidentAlert.alert_id == alert_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None
