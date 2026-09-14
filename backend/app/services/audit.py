"""AuditLog service — thin wrapper providing a write() API used by all services."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog
from app.repositories.audit_log import AuditLogRepository


class AuditService:
    """
    Centralized audit writer.

    Usage:
        audit = AuditService(session)
        await audit.log(
            AuditAction.user_login,
            organization_id=org_id,
            user_id=user.id,
            context={"email": user.email},
        )

    CRITICAL: Do NOT pass passwords, tokens, or hashes in `context`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditLogRepository(session)

    async def log(
        self,
        action: AuditAction | str,
        *,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | str | None = None,
        target_type: str | None = None,
        target_id: uuid.UUID | str | None = None,
        context: dict | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        **kwargs,
    ) -> AuditLog:
        act = action if isinstance(action, AuditAction) else AuditAction(action)
        res_type = resource_type or target_type
        res_id = resource_id or target_id
        ctx = context if context is not None else details
        return await self._repo.write(
            action=act,
            organization_id=organization_id,
            user_id=user_id,
            resource_type=res_type,
            resource_id=str(res_id) if res_id else None,
            context=ctx,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        action_filter: AuditAction | None = None,
    ) -> list[AuditLog]:
        return await self._repo.list_for_org(
            organization_id,
            limit=limit,
            offset=offset,
            action_filter=action_filter,
        )
