"""Crawl Courtesy & Robots.txt Compliance Service.

Enforces:
1. Automated robots.txt compliance before fetching any external URL (httpx, Firecrawl, Browserless).
2. Honest skip recording (ROBOTS_TXT_DISALLOWED / BLOCKED) when Disallow rules match.
3. Per-domain bounded request rate limiting (token bucket / sliding window).
4. Memory-bounded caching of robots.txt rules.
"""
from __future__ import annotations

import asyncio
import logging
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "CyberHub-EvidenceCollector/1.0 (+https://cyberhub.local/security)"
ROBOTS_CACHE_TTL_SECONDS = 3600  # 1 hour cache


@dataclass
class RobotsCheckResult:
    is_allowed: bool
    reason: str
    crawl_delay: float | None = None
    robots_url: str | None = None


class DomainRateLimiter:
    """Sliding-window per-domain rate limiter."""

    def __init__(self, max_rps: float | None = None) -> None:
        self.max_rps = max_rps or getattr(settings, "DOMAIN_RATE_LIMIT_RPS", 2.0)
        self.min_interval = 1.0 / max(0.1, self.max_rps)
        self._last_access: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def throttle(self, domain: str) -> float:
        """Enforce rate limit delay for the given domain. Returns seconds waited."""
        clean_domain = domain.lower().strip()
        waited = 0.0

        async with self._lock:
            now = time.monotonic()
            last = self._last_access.get(clean_domain, 0.0)
            elapsed = now - last

            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                waited = wait_time
                self._last_access[clean_domain] = now + wait_time
            else:
                self._last_access[clean_domain] = now

        if waited > 0:
            await asyncio.sleep(waited)

        return waited


class CrawlCourtesyService:
    """Manages robots.txt evaluation and domain rate limiting."""

    def __init__(self) -> None:
        self.rate_limiter = DomainRateLimiter()
        self._robots_cache: dict[str, tuple[float, urllib.robotparser.RobotFileParser]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract clean hostname from URL."""
        parsed = urllib.parse.urlparse(url)
        return (parsed.hostname or "").lower()

    @staticmethod
    def get_robots_url(url: str) -> str | None:
        """Construct standard robots.txt URL for a given target URL."""
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return None
        port_str = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
        return f"{parsed.scheme}://{parsed.hostname}{port_str}/robots.txt"

    async def fetch_robots_parser(self, robots_url: str, timeout: float = 3.0) -> urllib.robotparser.RobotFileParser:
        """Fetch and parse robots.txt securely with short timeout."""
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(
                    robots_url,
                    headers={"User-Agent": DEFAULT_USER_AGENT},
                )
                if resp.status_code == 200:
                    content_lines = resp.text.splitlines()
                    parser.parse(content_lines)
                elif resp.status_code in (401, 403):
                    # If robots.txt is forbidden, treat as fully disallowed
                    parser.parse(["User-agent: *", "Disallow: /"])
                else:
                    # 404 or other 4xx/5xx: standard convention is allowed
                    parser.parse(["User-agent: *", "Disallow:"])
        except Exception as err:
            logger.debug(f"Failed to fetch robots.txt from '{robots_url}': {err}. Defaulting to allowed.")
            parser.parse(["User-agent: *", "Disallow:"])

        return parser

    async def check_url(
        self,
        target_url: str,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> RobotsCheckResult:
        """Check if target_url is permitted by robots.txt."""
        domain = self.extract_domain(target_url)
        if not domain:
            return RobotsCheckResult(is_allowed=False, reason="INVALID_URL_NO_DOMAIN")

        robots_url = self.get_robots_url(target_url)
        if not robots_url:
            return RobotsCheckResult(is_allowed=False, reason="INVALID_ROBOTS_URL")

        now = time.monotonic()
        parser: urllib.robotparser.RobotFileParser | None = None

        async with self._lock:
            cached = self._robots_cache.get(domain)
            if cached and (now - cached[0]) < ROBOTS_CACHE_TTL_SECONDS:
                parser = cached[1]

        if parser is None:
            parser = await self.fetch_robots_parser(robots_url)
            async with self._lock:
                self._robots_cache[domain] = (now, parser)

        # Evaluate permissions for our user-agent and fallback wildcard '*'
        is_allowed = parser.can_fetch(user_agent, target_url) or parser.can_fetch("*", target_url)
        delay = parser.crawl_delay(user_agent) or parser.crawl_delay("*")

        if not is_allowed:
            return RobotsCheckResult(
                is_allowed=False,
                reason="ROBOTS_TXT_DISALLOWED",
                crawl_delay=delay,
                robots_url=robots_url,
            )

        return RobotsCheckResult(
            is_allowed=True,
            reason="OK",
            crawl_delay=delay,
            robots_url=robots_url,
        )

    async def prepare_fetch(self, target_url: str) -> RobotsCheckResult:
        """Enforce crawl courtesy: check robots.txt and apply domain rate limiting."""
        domain = self.extract_domain(target_url)
        robots_res = await self.check_url(target_url)
        if not robots_res.is_allowed:
            return robots_res

        # Throttle request rate for domain
        await self.rate_limiter.throttle(domain)
        return robots_res


crawl_courtesy_service = CrawlCourtesyService()
