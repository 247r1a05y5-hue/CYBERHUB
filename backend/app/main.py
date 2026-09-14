"""FastAPI application factory."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    CyberPlatformError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    configure_logging()
    logger.info("cyber_platform_startup", env=settings.app_env)

    # In production, validate configuration and enforce strict database connectivity
    if settings.is_production:
        settings.validate_production_constraints()

    try:
        from app.db.base import Base
        from app.db.session import engine, AsyncSessionLocal
        import app.models  # Load all ORM models for Base.metadata
        from app.models.organization import Organization
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        from sqlalchemy import select

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # STRICT ENVIRONMENT GATE: Default credentials are ONLY seeded in development and test environments
        if settings.app_env in ("development", "testing") and settings.allow_demo_seeding:
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Organization))
                org = res.scalars().first()
                if not org:
                    org = Organization(name="CyberHub Defense Org")
                    session.add(org)
                    await session.flush()

                    admin = User(
                        email=settings.seed_admin_email,
                        hashed_password=hash_password(settings.seed_admin_password),
                        full_name="System Administrator",
                        role=UserRole.ADMIN,
                        organization_id=org.id,
                        is_active=True,
                    )
                    analyst = User(
                        email=settings.seed_analyst_email,
                        hashed_password=hash_password(settings.seed_analyst_password),
                        full_name="Lead Analyst",
                        role=UserRole.ANALYST,
                        organization_id=org.id,
                        is_active=True,
                    )
                    session.add_all([admin, analyst])
                    await session.commit()
                    logger.info("cyber_platform_seeded_default_users", env=settings.app_env)
        elif settings.is_production:
            logger.info("cyber_platform_production_mode", default_credentials_blocked=True)
    except Exception as e:
        if settings.is_production:
            logger.error("cyber_platform_production_startup_failed", error=str(e))
            raise RuntimeError(f"FATAL: Production database connection failed: {e}") from e
        logger.warning(f"Database auto-initialization notice: {e}")

    yield
    logger.info("cyber_platform_shutdown")



def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Cyber Platform API",
        description="Secure enterprise cybersecurity platform foundation",
        version="0.1.0",
        docs_url="/api/docs" if settings.app_debug else None,
        redoc_url="/api/redoc" if settings.app_debug else None,
        openapi_url="/api/openapi.json" if settings.app_debug else None,
        lifespan=lifespan,
    )

    # ── Security headers middleware ──────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        return response

    # ── Request-ID middleware ────────────────────────────────────────────────
    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # ── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom Domain Exception handlers ────────────────────────────────────
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc)},
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError):
        return JSONResponse(
            status_code=429,
            content={"detail": str(exc)},
        )

    # ── Unhandled Exception handler ──────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception):
        rid = request.headers.get("X-Request-ID", "unknown")
        logger.error("unhandled_exception", exc_info=exc, request_id=rid)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred.",
                    "request_id": rid,
                }
            },
        )

    # ── Routers ─────────────────────────────────────────────────────────────
    from app.api.v1.router import api_router  # noqa: PLC0415
    from app.api.v1.endpoints.health import router as health_router  # noqa: PLC0415

    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_application()
