"""Alert repository."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert, AlertStatus
from app.models.analysis_result import Severity
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    async def get_by_dedup_key(self, dedup_key: str) -> Optional[Alert]:
        stmt = select(Alert).where(Alert.dedup_key == dedup_key)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_with_details(
        self, alert_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Optional[Alert]:
        stmt = (
            select(Alert)
            .options(
                selectinload(Alert.analysis),
                selectinload(Alert.assigned_to),
                selectinload(Alert.incident_links),
            )
            .where(
                Alert.id == alert_id,
                Alert.organization_id == organization_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: uuid.UUID,
        status: Optional[AlertStatus] = None,
        severity: Optional[Severity] = None,
        assigned_to_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Alert], int]:
        stmt = select(Alert).where(Alert.organization_id == organization_id)
        count_stmt = select(func.count(Alert.id)).where(Alert.organization_id == organization_id)

        if status is not None:
            stmt = stmt.where(Alert.status == status)
            count_stmt = count_stmt.where(Alert.status == status)
        if severity is not None:
            stmt = stmt.where(Alert.severity == severity)
            count_stmt = count_stmt.where(Alert.severity == severity)
        if assigned_to_id is not None:
            stmt = stmt.where(Alert.assigned_to_id == assigned_to_id)
            count_stmt = count_stmt.where(Alert.assigned_to_id == assigned_to_id)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            stmt.options(selectinload(Alert.assigned_to))
            .order_by(desc(Alert.created_at))
            .offset(offset)
            .limit(limit)
        )
        items_res = await self.session.execute(stmt)
        return list(items_res.scalars().all()), total

    async def update_alert(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        **updates: Any,
    ) -> Optional[Alert]:
        updates["updated_at"] = datetime.now(timezone.utc)
        stmt = (
            update(Alert)
            .where(Alert.id == alert_id, Alert.organization_id == organization_id)
            .values(**updates)
            .returning(Alert)
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.scalar_one_or_none()
