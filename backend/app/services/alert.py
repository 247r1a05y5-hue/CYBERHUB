"""Alert service."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.alert import Alert, AlertStatus
from app.models.analysis_result import Severity
from app.models.audit_log import AuditAction
from app.models.notification import NotificationType
from app.repositories.alert import AlertRepository
from app.schemas.alert import AlertCreate, AlertUpdate
from app.services.audit import AuditService
from app.services.notification import NotificationService


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AlertRepository(session)
        self.audit = AuditService(session)
        self.notification = NotificationService(session)

    async def get_alert(self, alert_id: uuid.UUID, organization_id: uuid.UUID) -> Alert:
        alert = await self.repo.get_with_details(alert_id, organization_id)
        if not alert:
            raise NotFoundError(f"Alert {alert_id} not found")
        return alert

    async def list_alerts(
        self,
        organization_id: uuid.UUID,
        status: Optional[AlertStatus] = None,
        severity: Optional[Severity] = None,
        assigned_to_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Alert], int]:
        return await self.repo.list_by_org(
            organization_id=organization_id,
            status=status,
            severity=severity,
            assigned_to_id=assigned_to_id,
            limit=limit,
            offset=offset,
        )

    async def create_alert(
        self,
        organization_id: uuid.UUID,
        alert_in: AlertCreate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Alert:
        # Generate deterministic dedup key if not provided
        dedup_key = alert_in.dedup_key
        if not dedup_key:
            key_raw = f"{organization_id}:{alert_in.title}:{alert_in.analysis_id or ''}"
            dedup_key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()

        # Check existing for deduplication
        existing = await self.repo.get_by_dedup_key(dedup_key)
        if existing and existing.status in (AlertStatus.open, AlertStatus.acknowledged):
            return existing

        alert = await self.repo.create(
            organization_id=organization_id,
            analysis_id=alert_in.analysis_id,
            assigned_to_id=alert_in.assigned_to_id,
            title=alert_in.title,
            description=alert_in.description,
            severity=alert_in.severity,
            status=alert_in.status,
            risk_score=alert_in.risk_score,
            dedup_key=dedup_key,
            tags=alert_in.tags or {},
        )

        await self.audit.log(
            organization_id=organization_id,
            action=AuditAction.create,
            target_type="alert",
            target_id=str(alert.id),
            user_id=actor_id,
            details={"title": alert.title, "severity": alert.severity.value},
        )

        return alert

    async def update_alert(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        alert_in: AlertUpdate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Alert:
        alert = await self.get_alert(alert_id, organization_id)
        updates = alert_in.model_dump(exclude_unset=True)

        updated = await self.repo.update_alert(alert_id, organization_id, **updates)
        if not updated:
            raise NotFoundError(f"Alert {alert_id} not found")

        await self.audit.log(
            organization_id=organization_id,
            action=AuditAction.update,
            target_type="alert",
            target_id=str(alert_id),
            user_id=actor_id,
            details={"updated_fields": list(updates.keys())},
        )

        # Notify assigned user if assigned_to changed
        if "assigned_to_id" in updates and updates["assigned_to_id"]:
            await self.notification.create_notification(
                organization_id=organization_id,
                user_id=updates["assigned_to_id"],
                title=f"Alert Assigned: {updated.title}",
                message=f"You have been assigned to alert {updated.title} ({updated.severity.value.upper()})",
                notification_type=NotificationType.alert_created,
                entity_type="alert",
                entity_id=str(alert_id),
            )

        return updated
