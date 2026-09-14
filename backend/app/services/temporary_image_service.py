"""Ephemeral Temporary Image Manager for External Search Engines.

Security Specifications:
- Cryptographically random 256-bit URL-safe token generation
- Strict TTL (default 10 minutes, max 30 minutes)
- In-memory ephemeral registry with auto-expiration cleanup
- Immediate deletion callback executed after provider calls complete (success or failure)
- No permanent storage or public directory publication of user images
"""
from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 600  # 10 minutes
MAX_TTL_SECONDS = 1800  # 30 minutes
MAX_ACCESS_COUNT = 10  # SearchAPI crawler safety limit


@dataclass
class TemporaryImageRecord:
    """Ephemeral in-memory image record."""
    token: str
    image_bytes: bytes
    content_type: str
    created_at: float
    expires_at: float
    access_count: int = 0


class TemporaryImageService:
    """Manages short-lived, authenticated temporary image endpoints for external crawlers."""

    def __init__(self) -> None:
        self._registry: dict[str, TemporaryImageRecord] = {}

    def _purge_expired(self) -> None:
        """Prune expired temporary images from the registry."""
        now = time.time()
        expired_keys = [k for k, v in self._registry.items() if now > v.expires_at]
        for k in expired_keys:
            self._registry.pop(k, None)

    def create_temporary_image(
        self,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        base_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Store image bytes under a cryptographically secure token and return (token, public_url).
        """
        self._purge_expired()

        clamped_ttl = min(max(ttl_seconds, 60), MAX_TTL_SECONDS)
        token = secrets.token_urlsafe(32)
        now = time.time()

        record = TemporaryImageRecord(
            token=token,
            image_bytes=image_bytes,
            content_type=content_type,
            created_at=now,
            expires_at=now + clamped_ttl,
            access_count=0,
        )
        self._registry[token] = record

        # Determine public base URL
        host_base = (base_url or getattr(settings, "PUBLIC_BASE_URL", "http://localhost:8000")).rstrip("/")
        public_url = f"{host_base}/api/v1/temp-images/{token}"

        logger.info(
            f"Created ephemeral temporary image URL for SearchAPI: "
            f"token={token[:8]}..., ttl={clamped_ttl}s, bytes={len(image_bytes)}"
        )
        return token, public_url

    def get_temporary_image(self, token: str) -> tuple[bytes, str] | None:
        """
        Retrieve image bytes and content type by token. Returns None if missing, expired, or access limit exceeded.
        """
        self._purge_expired()

        record = self._registry.get(token)
        if not record:
            return None

        if time.time() > record.expires_at:
            self._registry.pop(token, None)
            return None

        record.access_count += 1
        if record.access_count > MAX_ACCESS_COUNT:
            logger.warning(f"Temporary image token {token[:8]}... exceeded max access count ({MAX_ACCESS_COUNT}); deleting.")
            self._registry.pop(token, None)
            return None

        return record.image_bytes, record.content_type

    def delete_temporary_image(self, token: str) -> bool:
        """
        Explicitly delete a temporary image immediately after search completes.
        """
        existed = self._registry.pop(token, None) is not None
        if existed:
            logger.info(f"Deleted ephemeral temporary image token: {token[:8]}...")
        return existed

    def active_count(self) -> int:
        """Return number of currently active temporary images."""
        self._purge_expired()
        return len(self._registry)


temporary_image_service = TemporaryImageService()
