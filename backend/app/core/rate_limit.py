"""In-memory / Redis token-bucket rate limiter dependency."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request

from app.core.exceptions import RateLimitError

# Simple in-memory sliding window rate limiter
_request_history: dict[str, list[float]] = defaultdict(list)


def rate_limit(max_requests: int = 30, window_seconds: int = 60) -> Callable:
    """FastAPI dependency for rate limiting by IP / User ID."""

    async def _dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)
        key = f"{user_id or client_ip}:{request.url.path}"

        now = time.time()
        window_start = now - window_seconds

        # Clean old timestamps
        _request_history[key] = [t for t in _request_history[key] if t > window_start]

        if len(_request_history[key]) >= max_requests:
            raise RateLimitError(
                f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s."
            )

        _request_history[key].append(now)

    return _dependency
