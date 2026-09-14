"""AuditService — Programmatic audit trail recorder for CyberHub."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog


class AuditService:
    """Service to record immutable, append-only audit trail logs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: AuditAction | str,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        **kwargs,
    ) -> AuditLog:
        """Create an audit log entry. Never logs secrets or raw biometric embeddings."""
        actual_details = details if details is not None else context
        sanitized_details = self._sanitize(actual_details or {})
        actual_resource_type = resource_type or target_type
        actual_resource_id = str(resource_id or target_id) if (resource_id or target_id) else None

        audit_entry = AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            action=action if isinstance(action, AuditAction) else AuditAction(action),
            resource_type=actual_resource_type,
            resource_id=actual_resource_id,
            context=sanitized_details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(audit_entry)
        await self.session.flush()
        return audit_entry

    def _sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively scrub sensitive fields, credentials, API keys, and raw embedding vectors."""
        SENSITIVE_SUBSTRINGS = (
            "password",
            "token",
            "secret",
            "api_key",
            "apikey",
            "credential",
            "embedding",
            "vector",
            "raw_features",
        )
        scrubbed = {}
        for k, v in data.items():
            key_lower = k.lower()
            if any(sub in key_lower for sub in SENSITIVE_SUBSTRINGS):
                scrubbed[k] = "[REDACTED]"
            elif isinstance(v, dict):
                scrubbed[k] = self._sanitize(v)
            elif isinstance(v, list) and v and isinstance(v[0], float) and len(v) > 32:
                # Fallback: vector arrays that slipped through keyword check
                scrubbed[k] = "[REDACTED]"
            else:
                scrubbed[k] = v
        return scrubbed
