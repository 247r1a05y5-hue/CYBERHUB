"""Report schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, Field

from app.models.report import ReportFormat, ReportStatus
from app.schemas.common import ORMBase


class ReportGenerateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    analysis_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    format: ReportFormat = ReportFormat.markdown
    custom_notes: Optional[str] = None


class ReportResponse(ORMBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_by_id: Optional[uuid.UUID] = None
    analysis_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    title: str
    format: ReportFormat
    status: ReportStatus
    storage_path: Optional[str] = None
    content: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
