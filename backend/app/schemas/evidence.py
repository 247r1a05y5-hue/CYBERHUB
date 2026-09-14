"""Evidence schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field

from app.models.evidence import EvidenceType
from app.schemas.common import ORMBase


class EvidenceCreate(BaseModel):
    analysis_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    evidence_type: EvidenceType = EvidenceType.IMAGE_FILE
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    storage_path: Optional[str] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")


class EvidenceResponse(ORMBase):
    id: uuid.UUID
    analysis_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    uploaded_by_id: Optional[uuid.UUID] = None
    evidence_type: EvidenceType
    title: str
    description: Optional[str] = None
    storage_path: Optional[str] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    created_at: datetime
    updated_at: datetime
