"""Security utilities — password hashing (Argon2id) and JWT handling.

CRITICAL RULES:
- Never log raw passwords or tokens.
- Never return password hashes to callers.
- JWT secret MUST come from settings (env var), never hardcoded.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Password hashing ──────────────────────────────────────────────────────────
_hasher = PasswordHash([Argon2Hasher()])


def hash_password(password: str) -> str:
    """Hash a password using Argon2id. Never log the result."""
    return _hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a stored Argon2id hash."""
    try:
        return _hasher.verify(plain, hashed)
    except Exception:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(
    user_id: uuid.UUID | str | None = None,
    organization_id: uuid.UUID | str | None = None,
    role: str = "viewer",
    subject: uuid.UUID | str | None = None,
    email: str | None = None,
    **extra: Any,
) -> str:
    """Create a 15-minute JWT access token. Never log the returned token."""
    uid = user_id or subject
    if not uid:
        raise ValueError("user_id or subject is required to create access token")
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(uid),
        "org": str(organization_id) if organization_id else "",
        "role": str(role),
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if email:
        payload["email"] = email
    payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.
    Raises JWTError (jose) on failure — callers must catch.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


# ── Refresh tokens ────────────────────────────────────────────────────────────
def generate_refresh_token() -> str:
    """Generate a cryptographically secure 256-bit refresh token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hash of the raw token for storage. Never store the raw token."""
    return hashlib.sha256(token.encode()).hexdigest()
