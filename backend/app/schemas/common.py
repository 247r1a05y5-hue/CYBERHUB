"""Common schema definitions for pagination, timestamps, and standard responses."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar
import uuid

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class HealthStatus(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: dict[str, str] = Field(default_factory=dict)
