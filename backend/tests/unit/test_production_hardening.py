"""Tests for Phase 5 Production Hardening Constraints.

Verifies:
1. PostgreSQL production mode configuration validity.
2. SQLite development/test mode validity.
3. Strict prohibition of SQLite in production environments (no silent fallback).
4. Strict prohibition of default demo credentials in production.
"""
from __future__ import annotations

import pytest
from app.core.config import Settings


def test_production_postgresql_valid_config():
    """Verify production settings accept valid PostgreSQL configuration."""
    prod_settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://prod_user:secure_prod_pass@postgres.internal:5432/cyberplatform",
        app_secret_key="a_very_secure_long_random_production_secret_key_32bytes",
        jwt_secret_key="another_very_secure_long_random_jwt_secret_key_32bytes",
        allow_demo_seeding=False,
    )
    assert prod_settings.is_production is True
    # Validation should pass without throwing
    prod_settings.validate_production_constraints()


def test_production_prohibits_sqlite():
    """Verify production mode strictly forbids SQLite and raises ValueError."""
    prod_sqlite_settings = Settings(
        app_env="production",
        database_url="sqlite+aiosqlite:///./cyberplatform.db",
        app_secret_key="a_very_secure_long_random_production_secret_key_32bytes",
        jwt_secret_key="another_very_secure_long_random_jwt_secret_key_32bytes",
    )
    with pytest.raises(ValueError, match="SQLite database URL is strictly prohibited in production mode"):
        prod_sqlite_settings.validate_production_constraints()


def test_production_prohibits_default_secrets():
    """Verify production mode rejects default secrets."""
    prod_weak_secret = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://prod_user:prod_pass@postgres.internal:5432/cyberplatform",
        app_secret_key="changeme",
        jwt_secret_key="a_very_secure_long_random_jwt_secret_key_32bytes",
    )
    with pytest.raises(ValueError, match="Default APP_SECRET_KEY is prohibited in production"):
        prod_weak_secret.validate_production_constraints()


def test_development_allows_sqlite_and_demo_seeding():
    """Verify development/test settings allow SQLite and demo credentials."""
    dev_settings = Settings(
        app_env="development",
        database_url="sqlite+aiosqlite:///./cyberplatform.db",
        allow_demo_seeding=True,
    )
    assert dev_settings.is_production is False
    assert "sqlite" in dev_settings.database_url
    assert dev_settings.allow_demo_seeding is True


def test_testing_mode_allows_in_memory_or_file_sqlite():
    """Verify testing mode operates cleanly with isolated test SQLite."""
    test_settings = Settings(
        app_env="testing",
        database_url="sqlite+aiosqlite:///:memory:",
        allow_demo_seeding=False,
    )
    assert test_settings.is_production is False
    assert test_settings.app_env == "testing"
