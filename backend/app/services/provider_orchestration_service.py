"""External Search Provider Abstraction & Orchestration Layer.

Locked Strategy:
- PRIMARY: Google Cloud Vision — Web Detection (Real Adapter)
- SECONDARY: TinEye API / MatchEngine (Real Adapter)
- TEST HARNESS: DeterministicMockProvider (strictly guarded for test suites)
- Explicit Provider Status: NOT_CONFIGURED, READY, RUNNING, SUCCEEDED, FAILED, DEGRADED, RATE_LIMITED
- Circuit Breaker: Tracks consecutive failures and trips to degraded state
- Normalization: Retains full provider provenance and metadata
"""
from __future__ import annotations

import abc
import asyncio
import base64
import enum
import logging
import os
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


@dataclass(frozen=True)
class NormalizedDiscoveryResult:
    """Standardized discovery signal returned by an external search provider."""
    provider: str
    page_url: str
    image_url: str
    domain: str
    page_title: str
    discovered_at: datetime
    provider_score: float
    provider_raw_ref: str
    source_url: str = ""
    c2pa_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_url:
            object.__setattr__(self, "source_url", self.page_url or self.image_url)


@dataclass
class ProviderOptions:
    """Configurable execution parameters for provider calls."""
    max_results: int = 25
    include_similar: bool = True
    timeout_seconds: float = 15.0
    safe_search: bool = True


class CircuitBreaker:
    """Protects against cascade failures to external provider APIs."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 60.0,
        recovery_time_seconds: float | None = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_time_seconds if recovery_time_seconds is not None else recovery_timeout_seconds
        self.consecutive_failures = 0
        self.last_failure_time: float | None = None
        self.state: str = "CLOSED"  # CLOSED (healthy), OPEN (degraded), HALF_OPEN

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


class GoogleVisionWebDetectionProvider(ImageDiscoveryProvider):
    """Google Cloud Vision — Official Web Detection Client Adapter via Application Default Credentials (ADC)."""

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__("GoogleCloudVision")
        self.api_key = api_key or getattr(settings, "GOOGLE_VISION_API_KEY", None) or os.getenv("GOOGLE_VISION_API_KEY")
        self.endpoint = "https://vision.googleapis.com/v1/images:annotate"
        self._client: Any | None = None
        self._client_init_attempted: bool = False
        self._has_adc_credentials: bool | None = None

    def _get_client(self) -> Any | None:
        """Lazily initialize official Google Cloud Vision ImageAnnotatorClient via ADC."""
        if not self._client_init_attempted:
            self._client_init_attempted = True
            try:
                import google.auth
                from google.cloud import vision

                credentials, project = google.auth.default()
                if credentials:
                    self._client = vision.ImageAnnotatorClient(credentials=credentials)
                    self._has_adc_credentials = True
                    logger.info(f"Google Cloud Vision client initialized via ADC (project: {project or 'cyberhub-508511'})")
            except Exception as err:
                logger.debug(f"Google Cloud Vision ADC client initialization notice: {err}")
                self._client = None
                self._has_adc_credentials = False
        return self._client

    def get_status(self) -> ProviderStatus:
        if not self.circuit_breaker.allow_request():
            return ProviderStatus.DEGRADED

        client = self._get_client()
        if client or self.api_key:
            return ProviderStatus.READY
        return ProviderStatus.NOT_CONFIGURED

    async def discover(
        self,
        image_bytes: bytes,
        image_url: str | None,
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        """Query Google Cloud Vision Web Detection using actual stored reference image bytes."""
        status = self.get_status()
        if status == ProviderStatus.NOT_CONFIGURED:
            logger.info("Google Cloud Vision provider not configured (ADC / API key not found); skipping.")
            return []

        if status == ProviderStatus.DEGRADED or not self.circuit_breaker.allow_request():
            logger.warning("Google Cloud Vision circuit breaker is OPEN; request degraded.")
            return []

        logger.info(
            f"Google Cloud Vision Web Detection request dispatched: "
            f"image_size={len(image_bytes)} bytes, max_results={options.max_results}"
        )

        # 1. Primary path: Official Google Cloud Vision Client library (ADC)
        client = self._get_client()
        if client:
            try:
                try:
                    from google.cloud import vision
                    v_image = vision.Image(content=image_bytes)
                except ImportError:
                    v_image = {"content": image_bytes}

                def _call_vision_sync() -> Any:
                    return client.web_detection(image=v_image, max_results=options.max_results)

                response = await asyncio.to_thread(_call_vision_sync)

                if response.error.message:
                    self.circuit_breaker.record_failure()
                    logger.error(f"Google Cloud Vision Web Detection API returned error: {response.error.message}")
                    return []

                self.circuit_breaker.record_success()
                return self._parse_vision_response(response.web_detection, options)
            except Exception as err:
                self.circuit_breaker.record_failure()
                logger.error(f"Google Cloud Vision Web Detection client call failed: {err}")
                # If API key fallback is not configured, exit
                if not self.api_key:
                    return []

        # 2. REST API Key Fallback if ADC client call was not viable
        if self.api_key:
            return await self._discover_via_rest(image_bytes, options)

        return []

    def _parse_vision_response(
        self,
        web_detection: Any,
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        """Normalize protobuf or dict WebDetection response from Google Cloud Vision."""
        results: list[NormalizedDiscoveryResult] = []
        if not web_detection:
            logger.info("Google Cloud Vision returned empty webDetection payload.")
            return []

        # Extract entities and best guess labels for provenance enrichment
        web_entities = [
            {
                "entity_id": str(getattr(e, "entity_id", "") or (e.get("entityId") if isinstance(e, dict) else "")),
                "description": str(getattr(e, "description", "") or (e.get("description") if isinstance(e, dict) else "")),
                "score": float(getattr(e, "score", 0.0) or (e.get("score") if isinstance(e, dict) else 0.0)),
            }
            for e in (getattr(web_detection, "web_entities", []) or (web_detection.get("webEntities") if isinstance(web_detection, dict) else []))
            if getattr(e, "description", "") or (isinstance(e, dict) and e.get("description"))
        ]

        best_guess_labels = [
            str(getattr(b, "label", "") or (b.get("label") if isinstance(b, dict) else ""))
            for b in (getattr(web_detection, "best_guess_labels", []) or (web_detection.get("bestGuessLabels") if isinstance(web_detection, dict) else []))
            if getattr(b, "label", "") or (isinstance(b, dict) and b.get("label"))
        ]

        shared_meta = {
            "web_entities": web_entities,
            "best_guess_labels": best_guess_labels,
        }

        # 1. Full Matching Images
        full_matches = getattr(web_detection, "full_matching_images", []) or (web_detection.get("fullMatchingImages") if isinstance(web_detection, dict) else [])
        for item in full_matches:
            url = getattr(item, "url", "") or (item.get("url") if isinstance(item, dict) else "")
            if url:
                domain = urllib.parse.urlparse(url).netloc or "unknown"
                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        source_url=url,
                        page_url=url,
                        image_url=url,
                        domain=domain,
                        page_title=f"Full Matching Image ({domain})",
                        discovered_at=datetime.now(timezone.utc),
                        provider_score=1.0,
                        provider_raw_ref="full_matching_images",
                        c2pa_status=None,
                        metadata={"match_type": "FULL_MATCH", **shared_meta},
                    )
                )

        # 2. Partial Matching Images
        partial_matches = getattr(web_detection, "partial_matching_images", []) or (web_detection.get("partialMatchingImages") if isinstance(web_detection, dict) else [])
        for item in partial_matches:
            url = getattr(item, "url", "") or (item.get("url") if isinstance(item, dict) else "")
            if url:
                domain = urllib.parse.urlparse(url).netloc or "unknown"
                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        source_url=url,
                        page_url=url,
                        image_url=url,
                        domain=domain,
                        page_title=f"Partial Matching Image ({domain})",
                        discovered_at=datetime.now(timezone.utc),
                        provider_score=0.9,
                        provider_raw_ref="partial_matching_images",
                        c2pa_status=None,
                        metadata={"match_type": "PARTIAL_MATCH", **shared_meta},
                    )
                )

        # 3. Pages with Matching Images
        pages = getattr(web_detection, "pages_with_matching_images", []) or (web_detection.get("pagesWithMatchingImages") if isinstance(web_detection, dict) else [])
        for page in pages:
            p_url = getattr(page, "url", "") or (page.get("url") if isinstance(page, dict) else "")
            title = getattr(page, "page_title", "") or (page.get("pageTitle") if isinstance(page, dict) else "") or f"Page match on {urllib.parse.urlparse(p_url).netloc}"
            domain = urllib.parse.urlparse(p_url).netloc or "unknown"
            score = float(getattr(page, "score", 0.85) or (page.get("score") if isinstance(page, dict) else 0.85))

            img_url = p_url
            full_imgs = getattr(page, "full_matching_images", []) or (page.get("fullMatchingImages") if isinstance(page, dict) else [])
            part_imgs = getattr(page, "partial_matching_images", []) or (page.get("partialMatchingImages") if isinstance(page, dict) else [])
            if full_imgs:
                first = full_imgs[0]
                img_url = getattr(first, "url", "") or (first.get("url") if isinstance(first, dict) else p_url)
            elif part_imgs:
                first = part_imgs[0]
                img_url = getattr(first, "url", "") or (first.get("url") if isinstance(first, dict) else p_url)

            results.append(
                NormalizedDiscoveryResult(
                    provider=self.name,
                    source_url=p_url,
                    page_url=p_url,
                    image_url=img_url,
                    domain=domain,
                    page_title=title,
                    discovered_at=datetime.now(timezone.utc),
                    provider_score=score,
                    provider_raw_ref="pages_with_matching_images",
                    c2pa_status=None,
                    metadata={"match_type": "PAGE_MATCH", "page_score": score, **shared_meta},
                )
            )

        # 4. Visually Similar Images
        if options.include_similar:
            sim_images = getattr(web_detection, "visually_similar_images", []) or (web_detection.get("visuallySimilarImages") if isinstance(web_detection, dict) else [])
            for sim in sim_images:
                sim_url = getattr(sim, "url", "") or (sim.get("url") if isinstance(sim, dict) else "")
                if sim_url:
                    domain = urllib.parse.urlparse(sim_url).netloc or "unknown"
                    results.append(
                        NormalizedDiscoveryResult(
                            provider=self.name,
                            source_url=sim_url,
                            page_url=sim_url,
                            image_url=sim_url,
                            domain=domain,
                            page_title=f"Visually Similar Image ({domain})",
                            discovered_at=datetime.now(timezone.utc),
                            provider_score=0.75,
                            provider_raw_ref="visually_similar_images",
                            c2pa_status=None,
                            metadata={"match_type": "VISUALLY_SIMILAR", **shared_meta},
                        )
                    )

        logger.info(
            f"Google Cloud Vision Web Detection normalized {len(results)} candidate results "
            f"({len(web_entities)} entities, {len(best_guess_labels)} labels)"
        )
        return results

    async def _discover_via_rest(
        self,
        image_bytes: bytes,
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        """REST fallback when API key is provided."""
        b64_content = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "requests": [
                {
                    "image": {"content": b64_content},
                    "features": [{"type": "WEB_DETECTION", "maxResults": options.max_results}],
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=options.timeout_seconds) as client:
                resp = await client.post(
                    f"{self.endpoint}?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if resp.status_code == 429:
                self.circuit_breaker.record_failure()
                logger.error("Google Vision REST API rate limited (HTTP 429).")
                return []

            if resp.status_code != 200:
                self.circuit_breaker.record_failure()
                logger.error(f"Google Vision REST API returned HTTP {resp.status_code}: {resp.text[:200]}")
                return []

            self.circuit_breaker.record_success()
            data = resp.json()
            web_detection = data.get("responses", [{}])[0].get("webDetection", {})
            return self._parse_vision_response(web_detection, options)
        except Exception as err:
            self.circuit_breaker.record_failure()
            logger.error(f"Google Vision REST API call failed: {err}")
            return []


class TinEyeMatchEngineProvider(ImageDiscoveryProvider):
    """TinEye API / MatchEngine Adapter."""

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__("TinEye")
        self.api_key = api_key or getattr(settings, "TINEYE_API_KEY", None) or os.getenv("TINEYE_API_KEY")
        self.endpoint = "https://api.tineye.com/rest/search/"

    def get_status(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus.NOT_CONFIGURED
        if not self.circuit_breaker.allow_request():
            return ProviderStatus.DEGRADED
        return ProviderStatus.READY

    async def discover(
        self,
        image_bytes: bytes,
        image_url: str | None,
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        if not self.api_key:
            logger.info("TinEye API key not configured; skipping provider call.")
            return []

        if not self.circuit_breaker.allow_request():
            logger.warning("TinEye circuit breaker is OPEN; request degraded.")
            return []

        try:
            files = {"image": ("query.jpg", image_bytes, "image/jpeg")}
            async with httpx.AsyncClient(timeout=options.timeout_seconds) as client:
                resp = await client.post(
                    self.endpoint,
                    files=files,
                    headers={"X-API-Key": self.api_key},
                )

            if resp.status_code == 429:
                self.circuit_breaker.record_failure()
                logger.error("TinEye API rate limited (HTTP 429).")
                return []

            if resp.status_code != 200:
                self.circuit_breaker.record_failure()
                logger.error(f"TinEye API returned HTTP {resp.status_code}: {resp.text[:200]}")
                return []

            self.circuit_breaker.record_success()
            data = resp.json()
            results: list[NormalizedDiscoveryResult] = []

            for match in data.get("results", {}).get("matches", []):
                domain = match.get("domain", "tineye-match")
                backlinks = match.get("backlinks", [])
                p_url = backlinks[0].get("url") if backlinks else f"https://{domain}"
                img_url = backlinks[0].get("image_url") if backlinks else p_url
                score = float(match.get("score", 0.8))

                results.append(
                    NormalizedDiscoveryResult(
                        provider=self.name,
                        source_url=p_url,
                        page_url=p_url,
                        image_url=img_url,
                        domain=domain,
                        page_title=f"Match on {domain}",
                        discovered_at=datetime.now(timezone.utc),
                        provider_score=score,
                        provider_raw_ref=match.get("query_hash"),
                        c2pa_status=None,
                        metadata={"tineye_score": score, "overlay": match.get("overlay")},
                    )
                )

            return results
        except Exception as err:
            self.circuit_breaker.record_failure()
            logger.error(f"TinEye API call failed: {err}")
            return []


class SearchAPIGoogleLensProvider(ImageDiscoveryProvider):
    """
    SearchAPI Google Lens Provider — Dispatches requests to SearchAPI HTTP API (engine=google_lens).
    Receives real visual, exact, related, and knowledge graph matches and normalizes them into CYBERHUB candidate signals.
    """

    def __init__(self, api_key: str | None = None, engine: str = "google_lens") -> None:
        super().__init__("SearchAPIGoogleLens")
        self.api_key = api_key or getattr(settings, "SEARCHAPI_API_KEY", None) or os.getenv("SEARCHAPI_API_KEY")
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

        # Determine target image URL: use provided image_url or create ephemeral temp URL
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

        # Validate that the target image URL is externally reachable for SearchAPI crawlers
        parsed_target = urllib.parse.urlparse(target_url)
        target_host = (parsed_target.hostname or "").lower()
        if (
            target_host in ("localhost", "127.0.0.1", "0.0.0.0", "::1")
            or target_host.endswith(".local")
            or target_host.endswith(".internal")
        ):
            logger.error(
                f"Cannot dispatch SearchAPI request: target URL '{target_url}' is not externally reachable."
            )
            raise ValueError(
                "REFERENCE_IMAGE_NOT_EXTERNALLY_REACHABLE: Search provider requires an externally reachable HTTPS image URL. "
                "PUBLIC_BASE_URL is currently configured with a local/private address."
            )

        logger.info(
            f"SearchAPI Google Lens request dispatched: "
            f"target_url={target_url}, engine={self.engine}, max_results={options.max_results}"
        )

        try:
            params: dict[str, Any] = {
                "engine": self.engine,
                "url": target_url,
                "api_key": self.api_key,
            }

            async with httpx.AsyncClient(timeout=options.timeout_seconds) as http_client:
                response = await http_client.get(self.endpoint, params=params)

                if response.status_code in (401, 403):
                    self.circuit_breaker.record_failure()
                    logger.error(f"SearchAPI Authentication Error ({response.status_code}): Invalid or missing API key.")
                    raise PermissionError(f"PROVIDER_AUTH_ERROR: SearchAPI returned HTTP {response.status_code}")

                if response.status_code == 429:
                    self.circuit_breaker.record_failure()
                    logger.error("SearchAPI Rate/Quota Limit Exceeded (HTTP 429).")
                    raise RuntimeError("PROVIDER_QUOTA_EXCEEDED: SearchAPI monthly quota or rate limit reached.")

                if response.status_code != 200:
                    self.circuit_breaker.record_failure()
                    logger.error(f"SearchAPI HTTP Error {response.status_code}: {response.text[:200]}")
                    return []

                data = response.json()
                self.circuit_breaker.record_success()
                return self._parse_searchapi_response(data, options)

        except httpx.TimeoutException as timeout_err:
            self.circuit_breaker.record_failure()
            logger.error(f"SearchAPI Timeout after {options.timeout_seconds}s: {timeout_err}")
            raise TimeoutError(f"PROVIDER_TIMEOUT: SearchAPI request timed out: {timeout_err}") from timeout_err
        except (PermissionError, RuntimeError, TimeoutError, ValueError):
            raise
        except Exception as err:
            self.circuit_breaker.record_failure()
            logger.error(f"SearchAPI Google Lens discover failed: {err}")
            return []
        finally:
            if temp_token:
                from app.services.temporary_image_service import temporary_image_service
                temporary_image_service.delete_temporary_image(temp_token)

    def _parse_searchapi_response(
        self,
        data: dict[str, Any],
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        """Normalize SearchAPI Google Lens JSON response into standardized NormalizedDiscoveryResult records."""
        if not isinstance(data, dict):
            return []

        results: list[NormalizedDiscoveryResult] = []
        search_metadata = data.get("search_metadata", {})
        search_id = search_metadata.get("id", "")

        # 1. Exact Matches
        exact_matches = data.get("exact_matches", [])
        if isinstance(exact_matches, list):
            for item in exact_matches:
                if not isinstance(item, dict):
                    continue
                link = item.get("link") or item.get("url") or ""
                img_url = item.get("image") or item.get("thumbnail") or link
                thumb_url = item.get("thumbnail") or img_url
                title = item.get("title") or item.get("source") or "Exact Match"
                domain = item.get("source") or (urllib.parse.urlparse(link).netloc if link else "unknown")
                snippet = item.get("snippet") or ""

                if link or img_url:
                    results.append(
                        NormalizedDiscoveryResult(
                            provider=self.name,
                            source_url=link or img_url,
                            page_url=link or img_url,
                            image_url=img_url or link,
                            domain=domain,
                            page_title=title,
                            discovered_at=datetime.now(timezone.utc),
                            provider_score=1.0,
                            provider_raw_ref="exact_matches",
                            c2pa_status=None,
                            metadata={
                                "match_type": "EXACT",
                                "snippet": snippet,
                                "thumbnail_url": thumb_url,
                                "search_id": search_id,
                                "position": item.get("position"),
                            },
                        )
                    )

        # 2. Visual Matches
        visual_matches = data.get("visual_matches", [])
        if isinstance(visual_matches, list):
            for item in visual_matches:
                if not isinstance(item, dict):
                    continue
                link = item.get("link") or item.get("url") or ""
                img_url = item.get("image") or item.get("thumbnail") or link
                thumb_url = item.get("thumbnail") or img_url
                title = item.get("title") or item.get("source") or "Visual Match"
                domain = item.get("source") or (urllib.parse.urlparse(link).netloc if link else "unknown")
                snippet = item.get("snippet") or ""

                if link or img_url:
                    results.append(
                        NormalizedDiscoveryResult(
                            provider=self.name,
                            source_url=link or img_url,
                            page_url=link or img_url,
                            image_url=img_url or link,
                            domain=domain,
                            page_title=title,
                            discovered_at=datetime.now(timezone.utc),
                            provider_score=0.85,
                            provider_raw_ref="visual_matches",
                            c2pa_status=None,
                            metadata={
                                "match_type": "VISUALLY_SIMILAR",
                                "snippet": snippet,
                                "thumbnail_url": thumb_url,
                                "search_id": search_id,
                                "position": item.get("position"),
                            },
                        )
                    )

        # 3. Reverse Image Search (Pages with matching images / source pages)
        rev_search = data.get("reverse_image_search", {})
        if isinstance(rev_search, dict):
            pages = rev_search.get("pages_with_matching_images", [])
            if isinstance(pages, list):
                for item in pages:
                    if not isinstance(item, dict):
                        continue
                    link = item.get("link") or item.get("url") or ""
                    title = item.get("title") or "Source Page"
                    img_url = item.get("thumbnail") or item.get("image") or link
                    domain = item.get("source") or (urllib.parse.urlparse(link).netloc if link else "unknown")
                    snippet = item.get("snippet") or ""

                    if link or img_url:
                        results.append(
                            NormalizedDiscoveryResult(
                                provider=self.name,
                                source_url=link or img_url,
                                page_url=link or img_url,
                                image_url=img_url or link,
                                domain=domain,
                                page_title=title,
                                discovered_at=datetime.now(timezone.utc),
                                provider_score=0.90,
                                provider_raw_ref="reverse_image_search_pages",
                                c2pa_status=None,
                                metadata={
                                    "match_type": "SOURCE_PAGE",
                                    "snippet": snippet,
                                    "thumbnail_url": img_url,
                                    "search_id": search_id,
                                },
                            )
                        )

        # 4. Knowledge Graph & Related Searches
        knowledge_graph = data.get("knowledge_graph", [])
        if isinstance(knowledge_graph, list):
            for item in knowledge_graph:
                if not isinstance(item, dict):
                    continue
                link = item.get("link") or ""
                title = item.get("title") or "Knowledge Graph Entity"
                img_url = item.get("image") or item.get("thumbnail") or link
                domain = urllib.parse.urlparse(link).netloc if link else "google.com"

                if link or img_url:
                    results.append(
                        NormalizedDiscoveryResult(
                            provider=self.name,
                            source_url=link or img_url,
                            page_url=link or img_url,
                            image_url=img_url or link,
                            domain=domain,
                            page_title=title,
                            discovered_at=datetime.now(timezone.utc),
                            provider_score=0.75,
                            provider_raw_ref="knowledge_graph",
                            c2pa_status=None,
                            metadata={
                                "match_type": "RELATED",
                                "snippet": item.get("subtitle") or item.get("description", ""),
                                "search_id": search_id,
                            },
                        )
                    )

        return results[: options.max_results]


class DeterministicMockProvider(ImageDiscoveryProvider):
    """Test-only hermetic mock provider. Prohibited in production execution."""

    def __init__(self, fixtures: list[dict[str, Any]] | None = None) -> None:
        super().__init__("DeterministicMock")
        self.fixtures = fixtures or [
            {
                "domain": "social.example.test",
                "page_url": "https://social.example.test/post/88219",
                "image_url": "https://social.example.test/media/88219_full.png",
                "page_title": "Synthetic Test Post (social.example.test)",
                "score": 0.94,
                "threat_category": "SYNTHETIC_TEST_FIXTURE",
            },
            {
                "domain": "news.example.test",
                "page_url": "https://news.example.test/articles/409",
                "image_url": "https://news.example.test/img/asset_409.jpg",
                "page_title": "Synthetic Test Article (news.example.test)",
                "score": 0.88,
                "threat_category": "SYNTHETIC_TEST_FIXTURE",
            },
            {
                "domain": "archive.example.test",
                "page_url": "https://archive.example.test/media/item_12",
                "image_url": "https://archive.example.test/media/item_12.png",
                "page_title": "Synthetic Test Archive (archive.example.test)",
                "score": 0.78,
                "threat_category": "SYNTHETIC_TEST_FIXTURE",
            },
        ]

    def get_status(self) -> ProviderStatus:
        return ProviderStatus.READY

    async def discover(
        self,
        image_bytes: bytes,
        image_url: str | None,
        options: ProviderOptions,
    ) -> list[NormalizedDiscoveryResult]:
        # Production guard check
        is_test_env = (
            getattr(settings, "ALLOW_TEST_MOCK_PROVIDER", False)
            or os.getenv("ALLOW_TEST_MOCK_PROVIDER") == "true"
            or "pytest" in os.environ.get("_", "")
            or "PYTEST_CURRENT_TEST" in os.environ
        )
        if not is_test_env:
            raise PermissionError("DeterministicMockProvider is strictly prohibited in production discovery paths.")

        results: list[NormalizedDiscoveryResult] = []
        for f in self.fixtures:
            results.append(
                NormalizedDiscoveryResult(
                    provider=self.name,
                    source_url=f["page_url"],
                    page_url=f["page_url"],
                    image_url=f["image_url"],
                    domain=f["domain"],
                    page_title=f["page_title"],
                    discovered_at=datetime.now(timezone.utc),
                    provider_score=f.get("score", 0.9),
                    provider_raw_ref="mock_ref_001",
                    c2pa_status="NOT_PRESENT",
                    metadata={"threat_category": f.get("threat_category", "PUBLIC_WEB")},
                )
            )
        return results


class ProviderOrchestrationService:
    """Orchestrates multi-provider discovery with rate limits, budgets, and circuit breaking."""

    def __init__(self) -> None:
        self.searchapi_provider = SearchAPIGoogleLensProvider()
        self.google_provider = GoogleVisionWebDetectionProvider()
        self.tineye_provider = TinEyeMatchEngineProvider()
        self.mock_provider = DeterministicMockProvider()

    def get_provider_statuses(self) -> dict[str, dict[str, Any]]:
        """Return explicit status and configuration details for each provider."""
        searchapi_status = self.searchapi_provider.get_status()
        google_status = self.google_provider.get_status()
        tineye_status = self.tineye_provider.get_status()
        return {
            "searchapi_lens": {
                "name": "SearchAPI (Google Lens)",
                "status": searchapi_status.value,
                "configured": searchapi_status != ProviderStatus.NOT_CONFIGURED,
                "circuit_breaker": self.searchapi_provider.circuit_breaker.state,
                "engine": self.searchapi_provider.engine,
            },
            "google_vision": {
                "name": "Google Cloud Vision (Web Detection)",
                "status": google_status.value,
                "configured": google_status != ProviderStatus.NOT_CONFIGURED,
                "circuit_breaker": self.google_provider.circuit_breaker.state,
                "auth_method": "ADC" if self.google_provider._has_adc_credentials else ("API_KEY" if self.google_provider.api_key else "NONE"),
            },
            "tineye": {
                "name": "TinEye MatchEngine",
                "status": tineye_status.value,
                "configured": bool(self.tineye_provider.api_key),
                "circuit_breaker": self.tineye_provider.circuit_breaker.state,
            },
        }

    async def execute_discovery(
        self,
        image_bytes: bytes,
        image_url: str | None = None,
        options: ProviderOptions | None = None,
        use_mock_fallback: bool = False,
    ) -> list[NormalizedDiscoveryResult]:
        """Execute parallel discovery across active providers with error isolation."""
        opts = options or ProviderOptions()
        all_results: list[NormalizedDiscoveryResult] = []

        # Check if in test environment with mock fallback requested
        is_test_env = (
            getattr(settings, "ALLOW_TEST_MOCK_PROVIDER", False)
            or os.getenv("ALLOW_TEST_MOCK_PROVIDER") == "true"
            or "PYTEST_CURRENT_TEST" in os.environ
        )

        active_providers: list[ImageDiscoveryProvider] = []

        if is_test_env and use_mock_fallback:
            active_providers = [self.mock_provider]
        else:
            # Primary: SearchAPI Google Lens
            if self.searchapi_provider.get_status() == ProviderStatus.READY:
                active_providers.append(self.searchapi_provider)
            # Secondary optional: Google Vision (if enabled/ready)
            if getattr(settings, "GOOGLE_VISION_ENABLED", False) and self.google_provider.get_status() == ProviderStatus.READY:
                active_providers.append(self.google_provider)
            # Secondary optional: TinEye
            if self.tineye_provider.get_status() == ProviderStatus.READY:
                active_providers.append(self.tineye_provider)

        for prov in active_providers:
            try:
                res = await prov.discover(image_bytes, image_url, opts)
                all_results.extend(res)
            except Exception as err:
                logger.error(f"Provider '{prov.name}' failed during discovery: {err}")

        return all_results


provider_orchestrator = ProviderOrchestrationService()

