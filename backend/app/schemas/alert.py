"""Alert schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field

from app.models.alert import AlertStatus
from app.models.analysis_result import Severity
from app.schemas.common import ORMBase


class AlertCreate(BaseModel):
    analysis_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=3, max_length=500)
    description: Optional[str] = None
    severity: Severity = Severity.medium
    status: AlertStatus = AlertStatus.open
    assigned_to_id: Optional[uuid.UUID] = None
    risk_score: Optional[float] = None
    dedup_key: Optional[str] = None
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AlertUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[Severity] = None
    status: Optional[AlertStatus] = None
    assigned_to_id: Optional[uuid.UUID] = None
    tags: Optional[Dict[str, Any]] = None


class AlertResponse(ORMBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    analysis_id: Optional[uuid.UUID] = None
    assigned_to_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    severity: Severity
    status: AlertStatus
    risk_score: Optional[float] = None
    dedup_key: str
    tags: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
