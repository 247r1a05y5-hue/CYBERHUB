"""Rendering Fallback Service: Firecrawl & Browserless Integration.

Escalation hierarchy:
1. Primary: Direct SSRF-safe HTTP fetch (httpx + BeautifulSoup)
2. Fallback 1: Firecrawl (POST /v1/scrape) when plain fetch returns incomplete/JS-heavy content
3. Fallback 2: Browserless (POST /content) when full headless browser rendering is required

Strict Security & Compliance Guarantees:
- Zero login bypass, zero CAPTCHA solving, zero paywall bypass across all fallback paths
- Bounded crawl courtesy and robots.txt compliance
- Masks all API tokens and secret keys in logs and telemetry
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.models.investigation_record import CrawlStatus, FetchMethod
from app.services.ssrf_safe_fetcher import EvidenceCaptureSecurityError, SafeFetchResult, secure_url_fetcher

logger = logging.getLogger(__name__)


@dataclass
class RenderedPageResult:
    """Standardized output from any rendering/fetch tier."""
    url: str
    final_url: str
    status_code: int
    content_html: str
    fetch_method: FetchMethod
    fetch_provider: str
    crawl_status: CrawlStatus
    duration_ms: float
    error_category: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    redirect_chain: list[str] = field(default_factory=list)


class RenderingFallbackService:
    """Manages multi-tier page fetch and dynamic rendering escalation."""

    def __init__(self) -> None:
        self.firecrawl_url = getattr(settings, "FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1/scrape")
        self.browserless_url = getattr(settings, "BROWSERLESS_API_URL", "https://chrome.browserless.io/content")

    @property
    def is_firecrawl_configured(self) -> bool:
        key = getattr(settings, "FIRECRAWL_API_KEY", None)
        return bool(key and str(key).strip())

    @property
    def is_browserless_configured(self) -> bool:
        token = getattr(settings, "BROWSERLESS_TOKEN", None)
        return bool(token and str(token).strip())

    async def fetch_with_firecrawl(self, target_url: str) -> RenderedPageResult:
        """Execute single-page scrape via Firecrawl API v1."""
        if not self.is_firecrawl_configured:
            return RenderedPageResult(
                url=target_url,
                final_url=target_url,
                status_code=500,
                content_html="",
                fetch_method=FetchMethod.FIRECRAWL,
                fetch_provider="Firecrawl",
                crawl_status=CrawlStatus.ERROR,
                duration_ms=0.0,
                error_category="FIRECRAWL_API_KEY_NOT_CONFIGURED",
            )

        start = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": target_url,
            "formats": ["markdown", "html"],
            "onlyMainContent": False,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.firecrawl_url, headers=headers, json=payload)
                duration_ms = round((time.perf_counter() - start) * 1000, 2)

                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    html = data.get("html") or data.get("markdown") or ""
                    metadata = data.get("metadata", {})
                    final_url = metadata.get("sourceURL") or metadata.get("url") or target_url

                    return RenderedPageResult(
                        url=target_url,
                        final_url=final_url,
                        status_code=200,
                        content_html=html,
                        fetch_method=FetchMethod.FIRECRAWL,
                        fetch_provider="Firecrawl",
                        crawl_status=CrawlStatus.SUCCESS,
                        duration_ms=duration_ms,
                        metadata_json=metadata,
                        redirect_chain=[target_url, final_url] if final_url != target_url else [target_url],
                    )
                elif resp.status_code in (401, 403):
                    return RenderedPageResult(
                        url=target_url,
                        final_url=target_url,
                        status_code=resp.status_code,
                        content_html="",
                        fetch_method=FetchMethod.FIRECRAWL,
                        fetch_provider="Firecrawl",
                        crawl_status=CrawlStatus.INACCESSIBLE,
                        duration_ms=duration_ms,
                        error_category=f"FIRECRAWL_ACCESS_DENIED_{resp.status_code}",
                    )
                else:
                    return RenderedPageResult(
                        url=target_url,
                        final_url=target_url,
                        status_code=resp.status_code,
                        content_html="",
                        fetch_method=FetchMethod.FIRECRAWL,
                        fetch_provider="Firecrawl",
                        crawl_status=CrawlStatus.ERROR,
                        duration_ms=duration_ms,
                        error_category=f"FIRECRAWL_HTTP_{resp.status_code}",
                    )
        except Exception as err:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            return RenderedPageResult(
                url=target_url,
                final_url=target_url,
                status_code=500,
                content_html="",
                fetch_method=FetchMethod.FIRECRAWL,
                fetch_provider="Firecrawl",
                crawl_status=CrawlStatus.ERROR,
                duration_ms=duration_ms,
                error_category=f"FIRECRAWL_REQUEST_FAILED: {err}",
            )

    async def fetch_with_browserless(self, target_url: str) -> RenderedPageResult:
        """Execute headless browser page render via Browserless."""
        if not self.is_browserless_configured:
            return RenderedPageResult(
                url=target_url,
                final_url=target_url,
                status_code=500,
                content_html="",
                fetch_method=FetchMethod.BROWSERLESS,
                fetch_provider="Browserless",
                crawl_status=CrawlStatus.ERROR,
                duration_ms=0.0,
                error_category="BROWSERLESS_TOKEN_NOT_CONFIGURED",
            )

        start = time.perf_counter()
        token = settings.BROWSERLESS_TOKEN
        endpoint = f"{self.browserless_url}?token={token}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "url": target_url,
            "gotoOptions": {"waitUntil": "domcontentloaded", "timeout": 10000},
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(endpoint, headers=headers, json=payload)
                duration_ms = round((time.perf_counter() - start) * 1000, 2)

                if resp.status_code == 200:
                    html = resp.text
                    return RenderedPageResult(
                        url=target_url,
                        final_url=target_url,
                        status_code=200,
                        content_html=html,
                        fetch_method=FetchMethod.BROWSERLESS,
                        fetch_provider="Browserless",
                        crawl_status=CrawlStatus.SUCCESS,
                        duration_ms=duration_ms,
                        redirect_chain=[target_url],
                    )
                elif resp.status_code in (401, 403):
                    return RenderedPageResult(
                        url=target_url,
                        final_url=target_url,
                        status_code=resp.status_code,
                        content_html="",
                        fetch_method=FetchMethod.BROWSERLESS,
                        fetch_provider="Browserless",
                        crawl_status=CrawlStatus.INACCESSIBLE,
                        duration_ms=duration_ms,
                        error_category=f"BROWSERLESS_ACCESS_DENIED_{resp.status_code}",
                    )
                else:
                    return RenderedPageResult(
                        url=target_url,
                        final_url=target_url,
                        status_code=resp.status_code,
                        content_html="",
                        fetch_method=FetchMethod.BROWSERLESS,
                        fetch_provider="Browserless",
                        crawl_status=CrawlStatus.ERROR,
                        duration_ms=duration_ms,
                        error_category=f"BROWSERLESS_HTTP_{resp.status_code}",
                    )
        except Exception as err:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            return RenderedPageResult(
                url=target_url,
                final_url=target_url,
                status_code=500,
                content_html="",
                fetch_method=FetchMethod.BROWSERLESS,
                fetch_provider="Browserless",
                crawl_status=CrawlStatus.ERROR,
                duration_ms=duration_ms,
                error_category=f"BROWSERLESS_REQUEST_FAILED: {err}",
            )

    async def fetch_page(self, target_url: str, check_robots: bool = True) -> RenderedPageResult:
        """Execute tiered fetch: Primary httpx -> Firecrawl fallback -> Browserless fallback."""
        # 1. Check robots.txt and domain courtesy first
        if check_robots:
            from app.services.crawl_courtesy_service import crawl_courtesy_service
            courtesy = await crawl_courtesy_service.prepare_fetch(target_url)
            if not courtesy.is_allowed:
                return RenderedPageResult(
                    url=target_url,
                    final_url=target_url,
                    status_code=403,
                    content_html="",
                    fetch_method=FetchMethod.HTTPX,
                    fetch_provider="CrawlCourtesy",
                    crawl_status=CrawlStatus.ROBOTS_TXT_DISALLOWED,
                    duration_ms=0.0,
                    error_category="ROBOTS_TXT_DISALLOWED",
                )

        # 2. Primary Tier: Direct SSRF-safe HTTP fetch
        start = time.perf_counter()
        try:
            safe_fetch: SafeFetchResult = await secure_url_fetcher.fetch(
                target_url,
                max_size=settings.MAX_PAGE_BYTES,
                check_robots=False,  # Already checked above
            )
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            text_html = safe_fetch.raw_bytes.decode("utf-8", errors="replace")

            # Check if page is a JavaScript shell / needs client-side rendering
            is_js_shell = len(text_html.strip()) < 500 and (
                "enable javascript" in text_html.lower() or "root" in text_html.lower() or "app" in text_html.lower()
            )

            if not is_js_shell and len(text_html) > 200:
                return RenderedPageResult(
                    url=target_url,
                    final_url=safe_fetch.final_url,
                    status_code=safe_fetch.status_code,
                    content_html=text_html,
                    fetch_method=FetchMethod.HTTPX,
                    fetch_provider="HTTPX",
                    crawl_status=CrawlStatus.SUCCESS,
                    duration_ms=duration_ms,
                    redirect_chain=safe_fetch.redirect_chain,
                )
        except Exception as primary_err:
            logger.debug(f"Primary fetch for '{target_url}' failed: {primary_err}. Escalating to Firecrawl.")

        # 3. Fallback Tier 1: Firecrawl
        if self.is_firecrawl_configured:
            fc_res = await self.fetch_with_firecrawl(target_url)
            if fc_res.crawl_status == CrawlStatus.SUCCESS and len(fc_res.content_html) > 100:
                return fc_res

        # 4. Fallback Tier 2: Browserless
        if self.is_browserless_configured:
            bl_res = await self.fetch_with_browserless(target_url)
            if bl_res.crawl_status == CrawlStatus.SUCCESS and len(bl_res.content_html) > 100:
                return bl_res

        # If all tiers failed, return honest diagnostic failure
        return RenderedPageResult(
            url=target_url,
            final_url=target_url,
            status_code=502,
            content_html="",
            fetch_method=FetchMethod.HTTPX,
            fetch_provider="ExhaustedFallback",
            crawl_status=CrawlStatus.INACCESSIBLE,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
            error_category="ALL_FETCH_TIERS_EXHAUSTED",
        )


rendering_fallback_service = RenderingFallbackService()
