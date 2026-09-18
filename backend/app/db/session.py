"""Async SQLAlchemy engine and session factory."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

settings.validate_production_constraints()

is_sqlite = "sqlite" in settings.database_url
if is_sqlite and settings.is_production:
    raise RuntimeError("Production mode requires PostgreSQL. SQLite fallback is strictly prohibited in production.")

engine_kwargs: dict = {"echo": settings.app_debug}
if is_sqlite:
    engine_kwargs.update({"connect_args": {"check_same_thread": False, "timeout": 30}})
else:
    engine_kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})

engine = create_async_engine(settings.database_url_async, **engine_kwargs)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

async_session_factory = AsyncSessionLocal



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
