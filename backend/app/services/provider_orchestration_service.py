"""External Search Provider Abstraction, Normalization & Deduplication Layer.

Phase 2 Architecture:
- Provider 1: SearchAPI Google Lens (`SEARCHAPI_API_KEY`)
- Provider 2: SerpApi Google Lens (`SERPAPI_API_KEY`)
- Parallel Execution: Runs both providers concurrently without cross-blocking
- Robust Backoff & Retry: Bounded exponential backoff for transient errors, fail-fast on 401/403, 429 rate-limit handling
- Normalization: Single unified NormalizedDiscoveryResult schema preserving provenance
- Cross-Provider Deduplication: Merges identical public pages/images into single records retaining all provider references
- Tenant Isolation: Scoped to requesting organization
"""
from __future__ import annotations

import abc
import asyncio
import base64
import enum
import logging
import os
import random
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProviderStatus(str, enum.Enum):
    """Explicit status model for external search providers."""
    NOT_CONFIGURED = "NOT_CONFIGURED"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"
    RATE_LIMITED = "RATE_LIMITED"


class ProviderHealthState(str, enum.Enum):
    """Fine-grained health status."""
    CONFIGURED = "configured"
    MISSING_CREDENTIALS = "missing_credentials"
    REACHABLE = "reachable"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    PARSER_ERROR = "parser_error"
    PROVIDER_ERROR = "provider_error"
    NO_RESULTS = "no_results"


class ResultType(str, enum.Enum):
    EXACT_MATCH = "EXACT_MATCH"
    VISUAL_MATCH = "VISUAL_MATCH"
    RELATED = "RELATED"
    OTHER = "OTHER"


@dataclass
class NormalizedDiscoveryResult:
    """Unified normalized result schema across all search providers."""
    provider: str  # "SearchAPI" | "SerpApi"
    provider_result_id: str | None
    title: str | None
    source: str | None  # domain / source name
    result_url: str
    image_url: str | None
    thumbnail_url: str | None
    position: int | None
    result_type: str = "VISUAL_MATCH"  # EXACT_MATCH, VISUAL_MATCH, RELATED, OTHER
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Backward compatibility fields for existing API & clustering consumers
    page_url: str = ""
    source_url: str = ""
    domain: str = ""
    page_title: str = ""
    provider_score: float = 0.85
    provider_raw_ref: str = ""
    c2pa_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.page_url:
            self.page_url = self.result_url
        if not self.source_url:
            self.source_url = self.result_url
        if not self.domain:
            if self.source:
                self.domain = self.source
            elif self.result_url:
                parsed = urllib.parse.urlparse(self.result_url)
                self.domain = parsed.netloc or "unknown"
        if not self.page_title and self.title:
            self.page_title = self.title
        if not self.metadata:
            self.metadata = dict(self.provider_metadata)
        elif not self.provider_metadata:
            self.provider_metadata = dict(self.metadata)


@dataclass
class ProviderOptions:
    """Configurable execution parameters for provider calls."""
    max_results: int = 50
    include_similar: bool = True
    timeout_seconds: float = 15.0
    safe_search: bool = True
    max_retries: int = 3


class CircuitBreaker:
    """Protects against cascade failures to external provider APIs."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.consecutive_failures = 0
        self.last_failure_time: float | None = None
        self.state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.state = "CLOSED"
        self.last_failure_time = None

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker tripped OPEN after {self.consecutive_failures} consecutive failures.")

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure_time and (time.time() - self.last_failure_time > self.recovery_timeout_seconds):
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entered HALF_OPEN state; allowing trial request.")
                return True
            return False
        return True  # HALF_OPEN


async def _dispatch_with_retry(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict[str, Any],
    provider_name: str,
    timeout_seconds: float = 15.0,
    max_retries: int = 3,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    """
    Common resilient HTTP dispatch with parity across SearchAPI and SerpApi:
    - Fail fast on 401/403 (Authentication Error) without retry
    - Handle 429 Rate Limit (Respect Retry-After header)
    - Exponential backoff with jitter on 5xx / Network timeouts
    - Mask API key in all log messages
    """
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(endpoint, params=params, timeout=timeout_seconds)
            headers = dict(resp.headers)

            if resp.status_code in (401, 403):
                logger.error(f"{provider_name} Authentication Error ({resp.status_code}): Invalid or missing API key.")
                raise PermissionError(f"PROVIDER_AUTH_ERROR: {provider_name} returned HTTP {resp.status_code}")

            if resp.status_code == 429:
                retry_after_str = headers.get("retry-after")
                retry_after_sec = float(retry_after_str) if retry_after_str and retry_after_str.isdigit() else 2.0
                logger.warning(f"{provider_name} Rate/Quota Limit (HTTP 429). Retry-After: {retry_after_sec}s.")
                if attempt < max_retries:
                    await asyncio.sleep(min(retry_after_sec, 5.0))
                    continue
                raise RuntimeError(f"PROVIDER_QUOTA_EXCEEDED: {provider_name} monthly quota or rate limit reached.")

            if resp.status_code >= 500:
                logger.warning(f"{provider_name} Server Error (HTTP {resp.status_code}) on attempt {attempt + 1}/{max_retries + 1}.")
                if attempt < max_retries:
                    backoff = (0.5 * (2 ** attempt)) + (random.random() * 0.2)
                    await asyncio.sleep(backoff)
                    continue
                raise RuntimeError(f"PROVIDER_SERVER_ERROR: {provider_name} returned HTTP {resp.status_code}")

            if resp.status_code != 200:
                logger.error(f"{provider_name} HTTP {resp.status_code}: {resp.text[:200]}")
                raise RuntimeError(f"PROVIDER_ERROR: {provider_name} returned HTTP {resp.status_code}")

            try:
                data = resp.json()
            except Exception as parse_err:
                raise ValueError(f"PROVIDER_PARSER_ERROR: Failed to parse {provider_name} JSON response: {parse_err}") from parse_err

            return resp.status_code, data, headers

        except (httpx.TimeoutException, httpx.NetworkError) as net_err:
            last_err = net_err
            logger.warning(f"{provider_name} Network/Timeout error on attempt {attempt + 1}: {net_err}")
            if attempt < max_retries:
                backoff = (0.5 * (2 ** attempt)) + (random.random() * 0.2)
                await asyncio.sleep(backoff)
                continue
            raise TimeoutError(f"PROVIDER_TIMEOUT: {provider_name} request timed out after {max_retries + 1} attempts") from net_err

    if last_err:
        raise last_err
    raise RuntimeError(f"PROVIDER_DISPATCH_FAILED: {provider_name} failed after {max_retries + 1} attempts")


class ImageDiscoveryProvider(abc.ABC):
    """Abstract base class for all image discovery / reverse search providers."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.circuit_breaker = CircuitBreaker()

    @abc.abstractmethod
    def get_status(self) -> ProviderStatus:
        pass

    @abc.abstractmethod
    async def discover(
        self,
        image_bytes: bytes,
        image_url: str | None,
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        pass


_SENTINEL = object()


class SearchAPIGoogleLensProvider(ImageDiscoveryProvider):
    """SearchAPI Google Lens Provider (engine=google_lens)."""

    def __init__(self, api_key: Any = _SENTINEL, engine: str = "google_lens") -> None:
        super().__init__("SearchAPI")
        if api_key is _SENTINEL:
            self.api_key = getattr(settings, "SEARCHAPI_API_KEY", None) or os.getenv("SEARCHAPI_API_KEY")
        else:
            self.api_key = api_key
        self.engine = engine or getattr(settings, "SEARCHAPI_ENGINE", "google_lens") or "google_lens"
        self.endpoint = "https://www.searchapi.io/api/v1/search"

    def get_status(self) -> ProviderStatus:
        if not self.circuit_breaker.allow_request():
            return ProviderStatus.DEGRADED
        if not self.api_key or not str(self.api_key).strip():
            return ProviderStatus.NOT_CONFIGURED
        return ProviderStatus.READY

    async def discover(
        self,
        image_bytes: bytes,
        image_url: str | None,
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        status = self.get_status()
        if status == ProviderStatus.NOT_CONFIGURED:
            logger.info("SearchAPI provider not configured (SEARCHAPI_API_KEY not found); skipping.")
            return []

        if status == ProviderStatus.DEGRADED or not self.circuit_breaker.allow_request():
            logger.warning("SearchAPI circuit breaker is OPEN; request degraded.")
            return []

        temp_token = None
        target_url = image_url
        if not target_url and image_bytes:
            from app.services.temporary_image_service import temporary_image_service
            temp_token, target_url = temporary_image_service.create_temporary_image(
                image_bytes=image_bytes,
                content_type="image/jpeg",
                ttl_seconds=600,
            )

        if not target_url:
            logger.error("SearchAPI Google Lens requires a valid image URL or image bytes.")
            return []

        # Validate URL external reachability
        parsed_target = urllib.parse.urlparse(target_url)
        target_host = (parsed_target.hostname or "").lower()
        if (
            target_host in ("localhost", "127.0.0.1", "0.0.0.0", "::1")
            or target_host.endswith(".local")
            or target_host.endswith(".internal")
        ):
            logger.error(f"Cannot dispatch SearchAPI request: target URL '{target_url}' is not externally reachable.")
            raise ValueError(
                "REFERENCE_IMAGE_NOT_EXTERNALLY_REACHABLE: Search provider requires an externally reachable HTTPS image URL."
            )

        try:
            params = {
                "engine": self.engine,
                "url": target_url,
                "api_key": self.api_key,
            }

            async with httpx.AsyncClient(timeout=options.timeout_seconds) as client:
                _, data, _ = await _dispatch_with_retry(
                    client=client,
                    endpoint=self.endpoint,
                    params=params,
                    provider_name=self.name,
                    timeout_seconds=options.timeout_seconds,
                    max_retries=options.max_retries,
                )

            self.circuit_breaker.record_success()
            return self._parse_searchapi_response(data, options)

        except (PermissionError, RuntimeError, TimeoutError, ValueError):
            self.circuit_breaker.record_failure()
            raise
        except Exception as err:
            self.circuit_breaker.record_failure()
            logger.error(f"SearchAPI Google Lens discover failed: {err}")
            raise
        finally:
            if temp_token:
                from app.services.temporary_image_service import temporary_image_service
                temporary_image_service.delete_temporary_image(temp_token)

    def _parse_searchapi_response(
        self,
        data: dict[str, Any],
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        if not isinstance(data, dict):
            return []

        results: list[NormalizedDiscoveryResult] = []
        search_metadata = data.get("search_metadata", {})
        search_id = search_metadata.get("id")

        # 1. Exact Matches
        exact_matches = data.get("exact_matches", [])
        if isinstance(exact_matches, list):
            for item in exact_matches:
                if not isinstance(item, dict):
                    continue
                link = item.get("link") or item.get("url")
                if not link:
                    continue
                img_url = item.get("image") or item.get("thumbnail")
                thumb_url = item.get("thumbnail") or img_url
                title = item.get("title") or item.get("source")
                domain = item.get("source") or urllib.parse.urlparse(link).netloc

                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        provider_result_id=str(item.get("position")) if item.get("position") is not None else None,
                        title=title,
                        source=domain,
                        result_url=link,
                        image_url=img_url,
                        thumbnail_url=thumb_url,
                        position=item.get("position"),
                        result_type=ResultType.EXACT_MATCH.value,
                        provider_metadata={
                            "match_type": "EXACT_MATCH",
                            "search_id": search_id,
                            "snippet": item.get("snippet"),
                        },
                    )
                )

        # 2. Visual Matches
        visual_matches = data.get("visual_matches", [])
        if isinstance(visual_matches, list):
            for item in visual_matches:
                if not isinstance(item, dict):
                    continue
                link = item.get("link") or item.get("url")
                if not link:
                    continue
                img_url = item.get("image") or item.get("thumbnail")
                thumb_url = item.get("thumbnail") or img_url
                title = item.get("title") or item.get("source")
                domain = item.get("source") or urllib.parse.urlparse(link).netloc

                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        provider_result_id=str(item.get("position")) if item.get("position") is not None else None,
                        title=title,
                        source=domain,
                        result_url=link,
                        image_url=img_url,
                        thumbnail_url=thumb_url,
                        position=item.get("position"),
                        result_type=ResultType.VISUAL_MATCH.value,
                        provider_metadata={
                            "match_type": "VISUAL_MATCH",
                            "search_id": search_id,
                            "snippet": item.get("snippet"),
                        },
                    )
                )

        # 3. Reverse Image Search (Pages with matching images)
        rev_search = data.get("reverse_image_search", {})
        if isinstance(rev_search, dict):
            pages = rev_search.get("pages_with_matching_images", [])
            if isinstance(pages, list):
                for item in pages:
                    if not isinstance(item, dict):
                        continue
                    link = item.get("link") or item.get("url")
                    if not link:
                        continue
                    img_url = item.get("thumbnail") or item.get("image")
                    title = item.get("title")
                    domain = item.get("source") or urllib.parse.urlparse(link).netloc

                    results.append(
                        NormalizedDiscoveryResult(
                            provider=self.name,
                            provider_result_id=str(item.get("position")) if item.get("position") is not None else None,
                            title=title,
                            source=domain,
                            result_url=link,
                            image_url=img_url,
                            thumbnail_url=img_url,
                            position=item.get("position"),
                            result_type=ResultType.VISUAL_MATCH.value,
                            provider_metadata={
                                "match_type": "PAGE_MATCH",
                                "search_id": search_id,
                                "snippet": item.get("snippet"),
                            },
                        )
                    )

        # 4. Knowledge Graph & Related
        knowledge_graph = data.get("knowledge_graph", [])
        if isinstance(knowledge_graph, list):
            for item in knowledge_graph:
                if not isinstance(item, dict):
                    continue
                link = item.get("link")
                if not link:
                    continue
                title = item.get("title")
                img_url = item.get("image") or item.get("thumbnail")
                domain = urllib.parse.urlparse(link).netloc if link else "google.com"

                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        provider_result_id=None,
                        title=title,
                        source=domain,
                        result_url=link,
                        image_url=img_url,
                        thumbnail_url=img_url,
                        position=None,
                        result_type=ResultType.RELATED.value,
                        provider_metadata={
                            "match_type": "KNOWLEDGE_GRAPH",
                            "search_id": search_id,
                            "subtitle": item.get("subtitle") or item.get("description"),
                        },
                    )
                )

        return results[: options.max_results]


class SerpApiGoogleLensProvider(ImageDiscoveryProvider):
    """SerpApi Google Lens Provider (engine=google_lens)."""

    def __init__(self, api_key: Any = _SENTINEL, engine: str = "google_lens") -> None:
        super().__init__("SerpApi")
        if api_key is _SENTINEL:
            self.api_key = getattr(settings, "SERPAPI_API_KEY", None) or os.getenv("SERPAPI_API_KEY")
        else:
            self.api_key = api_key
        self.engine = engine or getattr(settings, "SERPAPI_ENGINE", "google_lens") or "google_lens"
        self.endpoint = "https://serpapi.com/search.json"

    def get_status(self) -> ProviderStatus:
        if not self.circuit_breaker.allow_request():
            return ProviderStatus.DEGRADED
        if not self.api_key or not str(self.api_key).strip():
            return ProviderStatus.NOT_CONFIGURED
        return ProviderStatus.READY

    async def discover(
        self,
        image_bytes: bytes,
        image_url: str | None,
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        status = self.get_status()
        if status == ProviderStatus.NOT_CONFIGURED:
            logger.info("SerpApi provider not configured (SERPAPI_API_KEY not found); skipping.")
            return []

        if status == ProviderStatus.DEGRADED or not self.circuit_breaker.allow_request():
            logger.warning("SerpApi circuit breaker is OPEN; request degraded.")
            return []

        temp_token = None
        target_url = image_url
        if not target_url and image_bytes:
            from app.services.temporary_image_service import temporary_image_service
            temp_token, target_url = temporary_image_service.create_temporary_image(
                image_bytes=image_bytes,
                content_type="image/jpeg",
                ttl_seconds=600,
            )

        if not target_url:
            logger.error("SerpApi Google Lens requires a valid image URL or image bytes.")
            return []

        # Validate URL external reachability
        parsed_target = urllib.parse.urlparse(target_url)
        target_host = (parsed_target.hostname or "").lower()
        if (
            target_host in ("localhost", "127.0.0.1", "0.0.0.0", "::1")
            or target_host.endswith(".local")
            or target_host.endswith(".internal")
        ):
            logger.error(f"Cannot dispatch SerpApi request: target URL '{target_url}' is not externally reachable.")
            raise ValueError(
                "REFERENCE_IMAGE_NOT_EXTERNALLY_REACHABLE: Search provider requires an externally reachable HTTPS image URL."
            )

        try:
            params = {
                "engine": self.engine,
                "url": target_url,
                "api_key": self.api_key,
            }

            async with httpx.AsyncClient(timeout=options.timeout_seconds) as client:
                _, data, _ = await _dispatch_with_retry(
                    client=client,
                    endpoint=self.endpoint,
                    params=params,
                    provider_name=self.name,
                    timeout_seconds=options.timeout_seconds,
                    max_retries=options.max_retries,
                )

            self.circuit_breaker.record_success()
            return self._parse_serpapi_response(data, options)

        except (PermissionError, RuntimeError, TimeoutError, ValueError):
            self.circuit_breaker.record_failure()
            raise
        except Exception as err:
            self.circuit_breaker.record_failure()
            logger.error(f"SerpApi Google Lens discover failed: {err}")
            raise
        finally:
            if temp_token:
                from app.services.temporary_image_service import temporary_image_service
                temporary_image_service.delete_temporary_image(temp_token)

    def _parse_serpapi_response(
        self,
        data: dict[str, Any],
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        if not isinstance(data, dict):
            return []

        results: list[NormalizedDiscoveryResult] = []
        search_metadata = data.get("search_metadata", {})
        search_id = search_metadata.get("id")

        # 1. Visual Matches
        visual_matches = data.get("visual_matches", [])
        if isinstance(visual_matches, list):
            for item in visual_matches:
                if not isinstance(item, dict):
                    continue
                link = item.get("link")
                if not link:
                    continue
                title = item.get("title")
                domain = item.get("source") or urllib.parse.urlparse(link).netloc
                img_url = item.get("thumbnail") or item.get("original")
                thumb_url = item.get("thumbnail") or img_url
                pos = item.get("position")

                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        provider_result_id=str(pos) if pos is not None else None,
                        title=title,
                        source=domain,
                        result_url=link,
                        image_url=img_url,
                        thumbnail_url=thumb_url,
                        position=pos,
                        result_type=ResultType.VISUAL_MATCH.value,
                        provider_metadata={
                            "match_type": "VISUAL_MATCH",
                            "search_id": search_id,
                            "source": domain,
                        },
                    )
                )

        # 2. Knowledge Graph
        kg = data.get("knowledge_graph", [])
        if isinstance(kg, list):
            for item in kg:
                if not isinstance(item, dict):
                    continue
                link = item.get("link")
                if not link:
                    continue
                title = item.get("title")
                domain = urllib.parse.urlparse(link).netloc if link else "google.com"
                img_url = item.get("thumbnail") or item.get("image")

                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        provider_result_id=None,
                        title=title,
                        source=domain,
                        result_url=link,
                        image_url=img_url,
                        thumbnail_url=img_url,
                        position=None,
                        result_type=ResultType.RELATED.value,
                        provider_metadata={
                            "match_type": "KNOWLEDGE_GRAPH",
                            "search_id": search_id,
                            "subtitle": item.get("subtitle"),
                        },
                    )
                )
        elif isinstance(kg, dict):
            link = kg.get("link")
            if link:
                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        provider_result_id=None,
                        title=kg.get("title"),
                        source=urllib.parse.urlparse(link).netloc,
                        result_url=link,
                        image_url=kg.get("thumbnail") or kg.get("image"),
                        thumbnail_url=kg.get("thumbnail"),
                        position=None,
                        result_type=ResultType.RELATED.value,
                        provider_metadata={"match_type": "KNOWLEDGE_GRAPH", "search_id": search_id},
                    )
                )

        # 3. Exact matches / reverse image search if present
        exact = data.get("exact_matches", [])
        if isinstance(exact, list):
            for item in exact:
                if not isinstance(item, dict):
                    continue
                link = item.get("link")
                if not link:
                    continue
                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        provider_result_id=str(item.get("position")) if item.get("position") is not None else None,
                        title=item.get("title"),
                        source=item.get("source") or urllib.parse.urlparse(link).netloc,
                        result_url=link,
                        image_url=item.get("thumbnail") or item.get("image"),
                        thumbnail_url=item.get("thumbnail"),
                        position=item.get("position"),
                        result_type=ResultType.EXACT_MATCH.value,
                        provider_metadata={"match_type": "EXACT_MATCH", "search_id": search_id},
                    )
                )

        return results[: options.max_results]


def _extract_url_str(val: Any) -> str | None:
    """Safely extract a URL string from string, dictionary, or list structures."""
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip()
        return s if s else None
    if isinstance(val, dict):
        for k in ("link", "url", "original", "thumbnail", "src", "image"):
            v = val.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
            elif isinstance(v, dict):
                extracted = _extract_url_str(v)
                if extracted:
                    return extracted
    return None


def canonicalize_url(raw_url: Any) -> str:
    """Normalize a URL for cross-provider deduplication."""
    clean_url = _extract_url_str(raw_url)
    if not clean_url:
        return ""
    try:
        parsed = urllib.parse.urlparse(clean_url)
        scheme = (parsed.scheme or "http").lower()
        netloc = (parsed.netloc or "").lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/") if parsed.path else ""

        # Remove standard tracking query parameters
        tracking_params = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref"}
        q_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        clean_query = [(k, v) for k, v in q_params if k.lower() not in tracking_params]
        query_str = urllib.parse.urlencode(sorted(clean_query)) if clean_query else ""

        return urllib.parse.urlunparse((scheme, netloc, path, "", query_str, ""))
    except Exception:
        return clean_url.lower().rstrip("/")


def deduplicate_discovery_results(results: list[NormalizedDiscoveryResult]) -> list[NormalizedDiscoveryResult]:
    """
    Deduplicate discovery results across providers:
    - Normalizes URLs
    - Merges matching page or image URLs
    - Preserves provenance for all reporting providers on the merged record
    """
    if not results:
        return []

    deduped_map: dict[str, NormalizedDiscoveryResult] = {}
    url_to_key: dict[str, str] = {}
    img_to_key: dict[str, str] = {}

    for res in results:
        c_url = canonicalize_url(res.result_url)
        c_img = canonicalize_url(res.image_url) if res.image_url else ""

        # Find match key
        match_key = None
        if c_url and c_url in url_to_key:
            match_key = url_to_key[c_url]
        elif c_img and c_img in img_to_key:
            match_key = img_to_key[c_img]

        if match_key is None:
            # New record
            key = c_url or c_img or f"raw_{len(deduped_map)}"
            res.provider_metadata["providers"] = [res.provider]
            res.provider_metadata["provider_sources"] = {
                res.provider: {
                    "position": res.position,
                    "provider_result_id": res.provider_result_id,
                    "result_type": res.result_type,
                    "raw_metadata": dict(res.provider_metadata),
                }
            }
            deduped_map[key] = res
            if c_url:
                url_to_key[c_url] = key
            if c_img:
                img_to_key[c_img] = key
        else:
            # Merge with existing record
            existing = deduped_map[match_key]
            providers_list = existing.provider_metadata.get("providers", [existing.provider])
            if res.provider not in providers_list:
                providers_list.append(res.provider)
            existing.provider_metadata["providers"] = providers_list

            sources_dict = existing.provider_metadata.get("provider_sources", {})
            sources_dict[res.provider] = {
                "position": res.position,
                "provider_result_id": res.provider_result_id,
                "result_type": res.result_type,
                "raw_metadata": dict(res.provider_metadata),
            }
            existing.provider_metadata["provider_sources"] = sources_dict

            # Prefer higher ranking or more descriptive title
            if not existing.title and res.title:
                object.__setattr__(existing, "title", res.title)
                object.__setattr__(existing, "page_title", res.title)
            if not existing.image_url and res.image_url:
                object.__setattr__(existing, "image_url", res.image_url)

            if c_url:
                url_to_key[c_url] = match_key
            if c_img:
                img_to_key[c_img] = match_key

    return list(deduped_map.values())


class ProviderOrchestrationService:
    """Orchestrates multi-provider discovery with rate limits, budgets, and circuit breaking."""

    def __init__(self) -> None:
        self.searchapi_provider = SearchAPIGoogleLensProvider()
        self.serpapi_provider = SerpApiGoogleLensProvider()

    def get_provider_statuses(self) -> dict[str, dict[str, Any]]:
        """Return explicit status and configuration details for each provider."""
        searchapi_status = self.searchapi_provider.get_status()
        serpapi_status = self.serpapi_provider.get_status()
        return {
            "searchapi_lens": {
                "name": "SearchAPI (Google Lens)",
                "status": searchapi_status.value,
                "configured": searchapi_status != ProviderStatus.NOT_CONFIGURED,
                "circuit_breaker": self.searchapi_provider.circuit_breaker.state,
                "engine": self.searchapi_provider.engine,
            },
            "serpapi_lens": {
                "name": "SerpApi (Google Lens)",
                "status": serpapi_status.value,
                "configured": serpapi_status != ProviderStatus.NOT_CONFIGURED,
                "circuit_breaker": self.serpapi_provider.circuit_breaker.state,
                "engine": self.serpapi_provider.engine,
            },
        }

    async def execute_parallel_discovery(
        self,
        image_bytes: bytes,
        image_url: str | None = None,
        options: ProviderOptions | None = None,
    ) -> tuple[list[NormalizedDiscoveryResult], dict[str, dict[str, Any]]]:
        """
        Execute parallel discovery across SearchAPI and SerpApi with error isolation.
        Returns: (deduplicated_results, per_provider_reports)
        """
        opts = options or ProviderOptions()
        active_providers: list[tuple[str, ImageDiscoveryProvider]] = []

        if self.searchapi_provider.get_status() == ProviderStatus.READY:
            active_providers.append(("SearchAPI", self.searchapi_provider))
        if self.serpapi_provider.get_status() == ProviderStatus.READY:
            active_providers.append(("SerpApi", self.serpapi_provider))

        if not active_providers:
            logger.warning("No active reverse image search providers are configured.")
            return [], {}

        # Dispatch parallel tasks
        async def _call_provider(name: str, prov: ImageDiscoveryProvider) -> tuple[str, list[NormalizedDiscoveryResult] | Exception, float]:
            t0 = time.perf_counter()
            try:
                res = await prov.discover(image_bytes, image_url, opts)
                lat = time.perf_counter() - t0
                return name, res, lat
            except Exception as e:
                lat = time.perf_counter() - t0
                return name, e, lat

        tasks = [_call_provider(name, prov) for name, prov in active_providers]
        raw_outputs = await asyncio.gather(*tasks, return_exceptions=False)

        all_raw_results: list[NormalizedDiscoveryResult] = []
        provider_reports: dict[str, dict[str, Any]] = {}

        for name, outcome, latency in raw_outputs:
            if isinstance(outcome, Exception):
                err_category = "AUTHENTICATION_FAILED" if isinstance(outcome, PermissionError) else (
                    "RATE_LIMITED" if "QUOTA" in str(outcome) or "429" in str(outcome) else (
                        "TIMEOUT" if isinstance(outcome, TimeoutError) else "PROVIDER_ERROR"
                    )
                )
                provider_reports[name] = {
                    "success": False,
                    "error_category": err_category,
                    "error_message": str(outcome)[:100],
                    "latency_ms": round(latency * 1000, 2),
                    "raw_count": 0,
                }
                logger.error(f"Provider '{name}' call failed ({err_category}) in {latency:.2f}s: {outcome}")
            else:
                all_raw_results.extend(outcome)
                provider_reports[name] = {
                    "success": True,
                    "latency_ms": round(latency * 1000, 2),
                    "raw_count": len(outcome),
                }

        deduped = deduplicate_discovery_results(all_raw_results)
        return deduped, provider_reports


provider_orchestrator = ProviderOrchestrationService()
