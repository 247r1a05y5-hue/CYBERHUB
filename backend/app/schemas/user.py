"""User schemas."""
from __future__ import annotations

from datetime import datetime
import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole
from app.schemas.common import ORMBase


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.ANALYST
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class UserResponse(ORMBase):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
