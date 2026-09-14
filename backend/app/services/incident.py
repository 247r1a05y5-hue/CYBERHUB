"""Incident service managing strict FSM transitions, notes, and alerts linking."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.alert import AlertStatus
from app.models.analysis_result import Severity
from app.models.audit_log import AuditAction
from app.models.incident import (
    INCIDENT_TRANSITIONS,
    STATUSES_REQUIRING_NOTE,
    Incident,
    IncidentStatus,
)
from app.models.note import Note
from app.models.notification import NotificationType
from app.repositories.alert import AlertRepository
from app.repositories.incident import IncidentAlertRepository, IncidentRepository, NoteRepository
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.audit import AuditService
from app.services.notification import NotificationService


class IncidentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IncidentRepository(session)
        self.note_repo = NoteRepository(session)
        self.alert_link_repo = IncidentAlertRepository(session)
        self.alert_repo = AlertRepository(session)
        self.audit = AuditService(session)
        self.notification = NotificationService(session)

    async def get_incident(self, incident_id: uuid.UUID, organization_id: uuid.UUID) -> Incident:
        incident = await self.repo.get_with_details(incident_id, organization_id)
        if not incident:
            raise NotFoundError(f"Incident {incident_id} not found")
        return incident

    async def list_incidents(
        self,
        organization_id: uuid.UUID,
        status: Optional[IncidentStatus] = None,
        severity: Optional[Severity] = None,
        owner_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Incident], int]:
        return await self.repo.list_by_org(
            organization_id=organization_id,
            status=status,
            severity=severity,
            owner_id=owner_id,
            limit=limit,
            offset=offset,
        )

    async def create_incident(
        self,
        organization_id: uuid.UUID,
        incident_in: IncidentCreate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Incident:
        incident = await self.repo.create(
            organization_id=organization_id,
            owner_id=incident_in.owner_id or actor_id,
            title=incident_in.title,
            description=incident_in.description,
            status=incident_in.status,
            severity=incident_in.severity,
            tags=incident_in.tags or {},
        )

        # Link any initial alerts
        if incident_in.alert_ids:
            for alert_id in incident_in.alert_ids:
                await self.alert_link_repo.link(incident.id, alert_id)
                # Auto update alert status to escalated
                await self.alert_repo.update_alert(
                    alert_id,
                    organization_id,
                    status=AlertStatus.escalated,
                )

        await self.audit.log(
            organization_id=organization_id,
            action=AuditAction.create,
            target_type="incident",
            target_id=str(incident.id),
            user_id=actor_id,
            details={"title": incident.title, "severity": incident.severity.value},
        )

        if incident.owner_id and incident.owner_id != actor_id:
            await self.notification.create_notification(
                organization_id=organization_id,
                user_id=incident.owner_id,
                title=f"Incident Assigned: {incident.title}",
                message=f"You have been assigned as owner for Incident '{incident.title}'",
                notification_type=NotificationType.incident_created,
                entity_type="incident",
                entity_id=str(incident.id),
            )

        return await self.get_incident(incident.id, organization_id)

    async def transition_status(
        self,
        incident_id: uuid.UUID,
        organization_id: uuid.UUID,
        target_status: IncidentStatus,
        note_content: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Incident:
        incident = await self.get_incident(incident_id, organization_id)
        current_status = incident.status

        if current_status == target_status:
            return incident

        allowed_transitions = INCIDENT_TRANSITIONS.get(current_status, [])
        if target_status not in allowed_transitions:
            raise ValidationError(
                f"Invalid transition from {current_status.value} to {target_status.value}. "
                f"Allowed: {[s.value for s in allowed_transitions]}"
            )

        if target_status in STATUSES_REQUIRING_NOTE and not (note_content and note_content.strip()):
            raise ValidationError(f"Transition to {target_status.value} requires a justification note")

        # Record note if provided
        if note_content and actor_id:
            await self.note_repo.create_note(
                incident_id=incident_id,
                author_id=actor_id,
                content=f"[Status change to {target_status.value.upper()}]: {note_content.strip()}",
            )

        updated = await self.repo.update_incident(
            incident_id=incident_id,
            organization_id=organization_id,
            status=target_status,
        )
        if not updated:
            raise NotFoundError(f"Incident {incident_id} not found")

        await self.audit.log(
            organization_id=organization_id,
            action=AuditAction.update,
            target_type="incident",
            target_id=str(incident_id),
            user_id=actor_id,
            details={"old_status": current_status.value, "new_status": target_status.value},
        )

        return await self.get_incident(incident_id, organization_id)

    async def add_note(
        self,
        incident_id: uuid.UUID,
        organization_id: uuid.UUID,
        content: str,
        author_id: uuid.UUID,
    ) -> Note:
        # Verify incident exists and belongs to org
        await self.get_incident(incident_id, organization_id)

        note = await self.note_repo.create_note(
            incident_id=incident_id,
            author_id=author_id,
            content=content,
        )

        await self.audit.log(
            organization_id=organization_id,
            action=AuditAction.create,
            target_type="note",
            target_id=str(note.id),
            user_id=author_id,
            details={"incident_id": str(incident_id)},
        )

        return note

    async def link_alert(
        self,
        incident_id: uuid.UUID,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Incident:
        incident = await self.get_incident(incident_id, organization_id)
        alert = await self.alert_repo.get_by_id_and_org(alert_id, organization_id)
        if not alert:
            raise NotFoundError(f"Alert {alert_id} not found")

        is_already_linked = await self.alert_link_repo.is_linked(incident_id, alert_id)
        if not is_already_linked:
            await self.alert_link_repo.link(incident_id, alert_id)
            await self.alert_repo.update_alert(alert_id, organization_id, status=AlertStatus.escalated)

            await self.audit.log(
                organization_id=organization_id,
                action=AuditAction.update,
                target_type="incident",
                target_id=str(incident_id),
                user_id=actor_id,
                details={"linked_alert_id": str(alert_id)},
            )

        return await self.get_incident(incident_id, organization_id)
