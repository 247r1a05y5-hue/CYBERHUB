"""Authentication schemas."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    organization_name: str = Field(min_length=2, max_length=255)
    role: Optional[str] = "admin"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    org_id: Optional[uuid.UUID] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    org_id: str
    role: str
    email: str
    exp: int
    iat: int
