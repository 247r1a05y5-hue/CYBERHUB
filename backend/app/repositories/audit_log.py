"""AuditLog repository — append-only writes, org-scoped reads."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog, AuditAction


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def write(
        self,
        action: AuditAction,
        *,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        context: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Write an immutable audit log entry.

        IMPORTANT: never pass passwords, tokens, or hashes in context.
        """
        entry = AuditLog(
            action=action,
            organization_id=organization_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            context=context,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        action_filter: AuditAction | None = None,
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        if action_filter:
            stmt = stmt.where(AuditLog.action == action_filter)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, id: uuid.UUID) -> AuditLog | None:
        return await self.session.get(AuditLog, id)
