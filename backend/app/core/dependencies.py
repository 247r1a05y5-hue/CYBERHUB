"""FastAPI dependencies — auth, RBAC, org & case isolation."""
from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.case import Case
from app.models.user import User, UserRole
from app.repositories.user import UserRepository

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate the JWT bearer token and return the authenticated user.

    organization_id comes ONLY from the verified token payload — never
    from client-controlled input (path params, query params, body).
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token has no subject."},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token subject is malformed."},
        )

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found or deactivated."},
        )

    # Attach to request state for access in middlewares / rate limiters
    request.state.user_id = str(user.id)
    request.state.organization_id = str(user.organization_id)

    return user


def require_roles(*roles: UserRole | str) -> Callable:
    """Dependency factory that enforces role-based access."""
    # Normalize strings or enums
    role_values = {r.value if isinstance(r, UserRole) else str(r) for r in roles}

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        user_role_val = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
        if user_role_val not in role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_ROLE",
                    "message": f"Required role(s): {list(role_values)}",
                },
            )
        return current_user

    return _check


# Convenience aliases
require_role = require_roles
require_admin = require_roles(UserRole.admin)
require_analyst_or_above = require_roles(UserRole.admin, UserRole.analyst)
require_any_role = require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)


def get_org_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    """Extract organization_id from the authenticated user."""
    return current_user.organization_id


async def get_case_for_user(
    case_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Case:
    """
    Fetch a Case and enforce cross-case / organization isolation.
    Guarantees users can only access cases belonging to their own organization.
    """
    stmt = select(Case).where(
        Case.id == case_id,
        Case.organization_id == current_user.organization_id,
    )
    result = await session.execute(stmt)
    case_obj = result.scalar_one_or_none()

    if not case_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CASE_NOT_FOUND", "message": f"Case with ID {case_id} not found."},
        )

    return case_obj
