"""Incident schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field

from app.models.analysis_result import Severity
from app.models.incident import IncidentStatus
from app.schemas.alert import AlertResponse
from app.schemas.common import ORMBase


class NoteCreate(BaseModel):
    content: str = Field(min_length=1)


class NoteResponse(ORMBase):
    id: uuid.UUID
    incident_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime
    updated_at: datetime


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    description: Optional[str] = None
    severity: Severity = Severity.medium
    status: IncidentStatus = IncidentStatus.new
    owner_id: Optional[uuid.UUID] = None
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict)
    alert_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)


class IncidentStatusTransition(BaseModel):
    status: IncidentStatus
    note: Optional[str] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[Severity] = None
    owner_id: Optional[uuid.UUID] = None
    tags: Optional[Dict[str, Any]] = None


class IncidentResponse(ORMBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    status: IncidentStatus
    severity: Severity
    tags: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    notes: Optional[List[NoteResponse]] = None
