"""Audit schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel

from app.models.audit_log import AuditAction
from app.schemas.common import ORMBase


class AuditLogResponse(ORMBase):
    id: uuid.UUID
    org_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: AuditAction
    target_type: str
    target_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
