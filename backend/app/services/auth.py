"""Authentication service — register, login, refresh, logout."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.config import settings
from app.models.audit_log import AuditAction
from app.models.user import User, UserRole
from app.repositories.organization import OrganizationRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse
from app.services.audit import AuditService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._org_repo = OrganizationRepository(session)
        self._rt_repo = RefreshTokenRepository(session)
        self._audit = AuditService(session)

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        organization_name: str | None = None,
        organization_slug: str | None = None,
        role: UserRole | str = UserRole.viewer,
        request_ip: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, TokenResponse]:
        """Register a new organization and/or user, returning user and token pair."""
        email = email.lower().strip()
        client_ip = request_ip or ip_address

        # Determine/create organization
        org = None
        slug = organization_slug or (organization_name.lower().replace(" ", "-") if organization_name else None)
        if slug:
            org = await self._org_repo.get_by_slug(slug)

        if not org and organization_name:
            import re
            base_slug = re.sub(r"[^a-z0-9\-]", "", organization_name.lower().replace(" ", "-")) or "org"
            final_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
            org = await self._org_repo.create(name=organization_name, slug=final_slug)
        elif not org and organization_slug:
            raise NotFoundError(f"Organization '{organization_slug}' not found.")
        elif not org:
            raise ConflictError("Organization name or slug required.")

        # Check email uniqueness
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise ConflictError("A user with this email already exists.")

        user_role = role if isinstance(role, UserRole) else UserRole(role.lower())
        hashed = hash_password(password)
        user = await self._user_repo.create(
            organization_id=org.id,
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            role=user_role,
            is_active=True,
            is_verified=True,
        )

        await self._audit.log(
            AuditAction.user_registered,
            organization_id=org.id,
            user_id=user.id,
            context={"email": email, "role": user_role.value},
            ip_address=client_ip,
        )

        # Issue token pair
        access = create_access_token(
            subject=user.id,
            organization_id=org.id,
            role=user.role.value,
            email=user.email,
        )
        refresh_raw = generate_refresh_token()
        refresh_hash = hash_token(refresh_raw)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        await self._rt_repo.create(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=client_ip,
        )

        tokens = TokenResponse(
            access_token=access,
            refresh_token=refresh_raw,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
        return user, tokens

    async def login(
        self,
        *,
        email: str,
        password: str,
        request_ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        """
        Authenticate user. Returns (access_token, refresh_token).
        Never log either token.
        """
        email = email.lower().strip()
        user = await self._user_repo.get_by_email(email)

        # Constant-time-ish rejection — always call verify_password to prevent timing attacks
        if not user or not verify_password(password, user.hashed_password):
            await self._audit.log(
                AuditAction.login_failed,
                context={"email": email},
                ip_address=request_ip,
            )
            raise AuthenticationError("Invalid credentials.")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated.")

        # Issue tokens
        access = create_access_token(user.id, user.organization_id, user.role.value)
        refresh_raw = generate_refresh_token()
        refresh_hash = hash_token(refresh_raw)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )

        await self._rt_repo.create(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=request_ip,
        )

        await self._audit.log(
            AuditAction.user_login,
            organization_id=user.organization_id,
            user_id=user.id,
            context={"email": email},
            ip_address=request_ip,
        )

        return access, refresh_raw  # caller must treat these as secrets

    async def refresh(
        self,
        *,
        refresh_token_raw: str,
        request_ip: str | None = None,
    ) -> tuple[str, str]:
        """
        Rotate refresh token. Returns (new_access_token, new_refresh_token).
        Old token is revoked (rotation enforced).
        """
        token_hash = hash_token(refresh_token_raw)
        db_token = await self._rt_repo.get_by_hash(token_hash)
        if not db_token:
            raise AuthenticationError("Refresh token is invalid or expired.")

        user = await self._user_repo.get_by_id(db_token.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or deactivated.")

        # Revoke old token (rotation)
        await self._rt_repo.revoke(db_token)

        # Issue new pair
        access = create_access_token(user.id, user.organization_id, user.role.value)
        new_refresh_raw = generate_refresh_token()
        new_refresh_hash = hash_token(new_refresh_raw)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        await self._rt_repo.create(
            user_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=expires_at,
            ip_address=request_ip,
        )

        await self._audit.log(
            AuditAction.token_refreshed,
            organization_id=user.organization_id,
            user_id=user.id,
            ip_address=request_ip,
        )

        return access, new_refresh_raw

    async def logout(
        self,
        *,
        refresh_token_raw: str,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        request_ip: str | None = None,
    ) -> None:
        """Revoke the specific refresh token (single-device logout)."""
        token_hash = hash_token(refresh_token_raw)
        db_token = await self._rt_repo.get_by_hash(token_hash)
        if db_token and db_token.user_id == user_id:
            await self._rt_repo.revoke(db_token)

        await self._audit.log(
            AuditAction.user_logout,
            organization_id=organization_id,
            user_id=user_id,
            ip_address=request_ip,
        )
