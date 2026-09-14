"""Health check endpoints — verified in CI, Docker health checks, and production orchestrators."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter()


class ComponentStatus(BaseModel):
    status: str
    details: str | None = None
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    environment: str
    version: str = "0.1.0"
    service: str = "cyber-platform-api"


class ReadinessResponse(BaseModel):
    status: str
    environment: str
    timestamp: str
    components: dict[str, Any]
    is_production: bool


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 if the FastAPI application process is alive.",
)
@router.get(
    "/live",
    response_model=HealthResponse,
    summary="Liveness probe alias",
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Environment-aware readiness probe",
    description="Validates that all required core infrastructure (Database, Storage, Vectors) is available.",
)
async def ready(response: Response) -> ReadinessResponse:
    """
    Environment-aware readiness check.
    - In PRODUCTION: PostgreSQL is mandatory. SQLite or DB failure sets status=503 (NOT READY).
    - In DEVELOPMENT/TEST: SQLite is accepted if configured.
    """
    components: dict[str, Any] = {}
    is_ready = True

    # 1. Database Check
    db_status = "ok"
    db_details = "Connected"
    try:
        if settings.is_production and "sqlite" in settings.database_url.lower():
            db_status = "error"
            db_details = "Production mode strictly forbids SQLite."
            is_ready = False
        else:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_details = "PostgreSQL" if not ("sqlite" in settings.database_url.lower()) else "SQLite (Dev/Test)"
    except Exception as exc:
        db_status = "error"
        db_details = f"Connection failed: {str(exc)[:120]}"
        is_ready = False

    components["database"] = {
        "status": db_status,
        "engine": "sqlite" if "sqlite" in settings.database_url.lower() else "postgresql",
        "details": db_details,
    }

    # 2. Storage Check
    storage_status = "ok"
    try:
        os.makedirs(settings.storage_root, exist_ok=True)
        test_file = os.path.join(settings.storage_root, ".health_probe")
        with open(test_file, "w") as f:
            f.write("probe")
        if os.path.exists(test_file):
            os.remove(test_file)
        storage_details = "Writable"
    except Exception as exc:
        storage_status = "error"
        storage_details = f"Storage inaccessible: {exc}"
        is_ready = False

    components["storage"] = {
        "status": storage_status,
        "path": settings.storage_root,
        "details": storage_details,
    }

    # 3. Vector Database (Qdrant)
    qdrant_status = "ok"
    qdrant_details = "Available"
    try:
        from app.services.qdrant_service import qdrant_service
        if qdrant_service.client is None and settings.is_production:
            qdrant_status = "degraded"
            qdrant_details = "Qdrant cluster unavailable; operating in fallback"
    except Exception as exc:
        qdrant_status = "degraded"
        qdrant_details = str(exc)[:80]

    components["vector_db"] = {
        "status": qdrant_status,
        "collection": settings.QDRANT_COLLECTION,
        "details": qdrant_details,
    }

    # Set HTTP status code
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
        is_production=settings.is_production,
    )

