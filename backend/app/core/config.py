"""Application configuration — loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    app_env: Literal["development", "testing", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = "changeme"
    log_level: str = "INFO"

    # ── JWT ─────────────────────────────────────────────────────────────────
    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # ── Database ────────────────────────────────────────────────────────────
    # Production defaults to PostgreSQL; development/testing can use SQLite when enabled
    database_url: str = "sqlite+aiosqlite:///./cyberplatform.db"
    allow_sqlite_fallback: bool = False

    @property
    def database_url_async(self) -> str:
        """Normalized async database connection URL for SQLAlchemy asyncpg engine."""
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def database_url_sync(self) -> str:
        """Normalized sync database connection URL for Alembic migrations and sync drivers."""
        url = self.database_url.strip()
        if "sqlite" in url:
            return url.replace("sqlite+aiosqlite://", "sqlite://")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        return url

    # ── Security & Production Constraints ───────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_production_constraints(self) -> None:
        """Validate that production environments strictly enforce PostgreSQL, non-wildcard CORS, and secure configs."""
        if self.is_production:
            if not self.database_url or "sqlite" in self.database_url.lower():
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: PostgreSQL DATABASE_URL is strictly mandatory in production mode. "
                    "SQLite database URL is strictly prohibited in production mode."
                )
            if self.allow_sqlite_fallback:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: allow_sqlite_fallback cannot be True in production mode."
                )
            if self.app_secret_key in ("changeme", "secret", "default", ""):
                raise ValueError("CRITICAL SECURITY ERROR: Default APP_SECRET_KEY is prohibited in production.")
            if self.jwt_secret_key in ("changeme", "secret", "default", ""):
                raise ValueError("CRITICAL SECURITY ERROR: Default JWT_SECRET_KEY is prohibited in production.")
            if "*" in self.cors_origins_list:
                raise ValueError("CRITICAL SECURITY ERROR: Wildcard CORS origins ('*') are strictly prohibited in production.")

    # ── Redis ───────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    @property
    def REDIS_URL(self) -> str:
        return self.redis_url

    # ── RQ ──────────────────────────────────────────────────────────────────
    rq_queue_name: str = "analysis"
    rq_max_retries: int = 3
    rq_retry_delay_seconds: int = 60

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    frontend_origin: str | None = None
    cors_allow_credentials: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.frontend_origin and self.frontend_origin.strip():
            origins.append(self.frontend_origin.strip())
        # If in production, filter out any wildcards
        if self.is_production:
            origins = [o for o in origins if o != "*"]
        return list(dict.fromkeys(origins))

    # ── File Storage ────────────────────────────────────────────────────────
    storage_root: str = "./storage"
    STORAGE_PATH: str = "./storage"
    STORAGE_DIR: str = "./storage"
    quarantine_root: str = "./quarantine"
    max_upload_bytes: int = 52_428_800  # 50 MB

    # ── Vector Database (Qdrant) ────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION: str = "cyberhub_image_embeddings"

    # ── Image Exposure Investigation & Search Providers ────────────────────
    DINOV2_MODEL_NAME: str = "dinov2_vits14"
    RATE_LIMIT_SCANS_PER_HOUR: int = 20
    COST_BUDGET_PER_ORG_MONTHLY_USD: float = 50.0
    SEARCHAPI_ENABLED: bool = True
    SEARCHAPI_API_KEY: str | None = None
    SEARCHAPI_ENGINE: str = "google_lens"
    GOOGLE_VISION_ENABLED: bool = False
    GOOGLE_VISION_API_KEY: str | None = None
    TINEYE_API_KEY: str | None = None
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    ALLOW_TEST_MOCK_PROVIDER: bool = False

    # ── Rate Limiting ───────────────────────────────────────────────────────
    login_rate_limit: str = "10/minute"

    # ── Seed / Demo (STRICTLY DEVELOPMENT & TEST ONLY) ──────────────────────
    allow_demo_seeding: bool = True
    seed_admin_email: str = "admin@cyber.local"
    seed_admin_password: str = "Admin1234!"
    seed_analyst_email: str = "analyst@cyberhub.security"
    seed_analyst_password: str = "Password123!"
    seed_viewer_email: str = "viewer@cyber.local"
    seed_viewer_password: str = "Viewer1234!"



@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()


settings = get_settings()

