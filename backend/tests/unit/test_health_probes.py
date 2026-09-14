"""Tests for Health Probes (Liveness & Readiness) and Production Database Enforcement."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app


@pytest.mark.asyncio
async def test_liveness_probe():
    """Liveness probe /health returns 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "ready")
        assert "environment" in data


@pytest.mark.asyncio
async def test_readiness_probe_dev_mode():
    """Readiness probe /health/ready returns status with component breakdown."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "environment" in data
        assert "components" in data
        assert "database" in data["components"]
        assert "storage" in data["components"]
        assert "vector_db" in data["components"]


def test_production_sqlite_rejection():
    """Validates that production mode strictly rejects SQLite and enforces PostgreSQL."""
    # 1. Reject sqlite database URL in production via validate_production_constraints()
    bad_sqlite_settings = Settings(
        app_env="production",
        database_url="sqlite+aiosqlite:///./test.db",
        jwt_secret_key="a" * 64,
        cors_origins="https://hub.example.com",
    )
    with pytest.raises(ValueError, match="SQLite database URL is strictly prohibited"):
        bad_sqlite_settings.validate_production_constraints()

    # 2. Reject dev mode flag in production
    bad_dev_flag_settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres:pass@localhost:5432/db",
        app_secret_key="b" * 64,
        jwt_secret_key="a" * 64,
        allow_sqlite_fallback=True,
        cors_origins="https://hub.example.com",
    )
    with pytest.raises(ValueError, match="allow_sqlite_fallback cannot be True in production"):
        bad_dev_flag_settings.validate_production_constraints()

    # 3. Valid production configuration with PostgreSQL passes without error
    valid_settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres:pass@localhost:5432/cyberhub",
        app_secret_key="c" * 64,
        jwt_secret_key="a" * 64,
        allow_sqlite_fallback=False,
        cors_origins="https://hub.example.com",
    )
    assert valid_settings.app_env == "production"
    assert "postgresql" in str(valid_settings.database_url)
    valid_settings.validate_production_constraints()  # Does not raise
