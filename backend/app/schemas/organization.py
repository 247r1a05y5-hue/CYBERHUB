"""Organization schemas."""
from __future__ import annotations

from datetime import datetime
import uuid
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)


class OrganizationResponse(ORMBase):
    id: uuid.UUID
    name: str
    created_at: datetime
