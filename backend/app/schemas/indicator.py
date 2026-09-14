"""Indicator schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field

from app.models.indicator import IndicatorType
from app.schemas.common import ORMBase


class IndicatorCreate(BaseModel):
    analysis_id: uuid.UUID
    indicator_type: IndicatorType = IndicatorType.other
    value: str = Field(min_length=1, max_length=2048)
    context: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)


class IndicatorResponse(ORMBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    analysis_id: uuid.UUID
    indicator_type: IndicatorType
    value: str
    context: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime
