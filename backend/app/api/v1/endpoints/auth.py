"""Authentication API endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.services.auth import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization and admin user",
)
async def register(
    req: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    auth_service = AuthService(session)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    user, tokens = await auth_service.register(
        email=req.email,
        password=req.password,
        organization_name=req.organization_name,
        role=req.role or "admin",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive tokens",
)
async def login(
    req: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    auth_service = AuthService(session)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token, refresh_token = await auth_service.login(
        email=req.email,
        password=req.password,
        request_ip=ip_address,
        user_agent=user_agent,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=86400,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token with rotating refresh token",
)
async def refresh(
    req: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    auth_service = AuthService(session)
    ip_address = request.client.host if request.client else None

    access_token, refresh_token = await auth_service.refresh(
        refresh_token_raw=req.refresh_token,
        request_ip=ip_address,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=86400,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke refresh token and terminate session",
)
async def logout(
    req: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    auth_service = AuthService(session)
    ip_address = request.client.host if request.client else None
    await auth_service.logout(
        refresh_token_raw=req.refresh_token,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        request_ip=ip_address,
    )
    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get profile of current authenticated user",
)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        org_id=current_user.organization_id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
