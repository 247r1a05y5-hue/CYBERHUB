"""Page Investigation Service.

Orchestrates full-page investigation:
- SSRF checks and robots.txt validation
- Tiered HTML fetch and rendering fallback
- Social platform public-boundary inspection
- Metadata extraction (title, description, canonical link, OpenGraph, Twitter tags)
- Public candidate image extraction
- DB persistence of PageInvestigation record
"""
from __future__ import annotations

import logging
import re
import urllib.parse
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.investigation_record import CrawlStatus, FetchMethod, PageInvestigation
from app.services.public_image_extractor import ExtractedImageCandidate, public_image_extractor
from app.services.rendering_fallback_service import RenderedPageResult, rendering_fallback_service

logger = logging.getLogger(__name__)

SOCIAL_PLATFORMS = {
    "instagram.com": "INSTAGRAM",
    "facebook.com": "FACEBOOK",
    "twitter.com": "TWITTER_X",
    "x.com": "TWITTER_X",
    "linkedin.com": "LINKEDIN",
    "tiktok.com": "TIKTOK",
    "youtube.com": "YOUTUBE",
    "pinterest.com": "PINTEREST",
    "reddit.com": "REDDIT",
}


@dataclass
class PageInvestigationResult:
    page_investigation: PageInvestigation
    candidate_image_urls: list[ExtractedImageCandidate]
    is_social_platform: bool
    platform_name: str | None = None


class PageInvestigationService:
    """Investigates individual discovered web pages and extracts forensic metadata."""

    @staticmethod
    def identify_social_platform(url: str) -> tuple[bool, str | None]:
        """Detect if target URL belongs to a major social media platform."""
        try:
            domain = (urllib.parse.urlparse(url).hostname or "").lower()
            for key, name in SOCIAL_PLATFORMS.items():
                if domain == key or domain.endswith("." + key):
                    return True, name
        except Exception:
            pass
        return False, None

    @staticmethod
    def extract_metadata_from_html(html_text: str, base_url: str) -> dict[str, Any]:
        """Extract title, description, canonical, OG, and Twitter metadata from HTML."""
        meta: dict[str, Any] = {
            "title": None,
            "description": None,
            "canonical": None,
            "opengraph": {},
            "twitter": {},
            "visible_text_snippet": None,
        }

        if not html_text or not isinstance(html_text, str):
            return meta

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, "html.parser")

            # Title
            if soup.title and soup.title.string:
                meta["title"] = soup.title.string.strip()

            # Description
            desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
            if desc_tag and desc_tag.get("content"):
                meta["description"] = desc_tag.get("content").strip()

            # Canonical
            canon_tag = soup.find("link", rel=re.compile(r"^canonical$", re.I))
            if canon_tag and canon_tag.get("href"):
                meta["canonical"] = urllib.parse.urljoin(base_url, canon_tag.get("href").strip())

            # OpenGraph
            og: dict[str, str] = {}
            for tag in soup.find_all("meta", property=re.compile(r"^og:", re.I)):
                prop = tag.get("property", "").lower()
                val = tag.get("content")
                if prop and val:
                    og[prop] = val.strip()
            meta["opengraph"] = og

            # Twitter
            tw: dict[str, str] = {}
            for tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
                name = tag.get("name", "").lower()
                val = tag.get("content")
                if name and val:
                    tw[name] = val.strip()
            meta["twitter"] = tw

            # Fallback title/description from OG if missing
            if not meta["title"] and "og:title" in og:
                meta["title"] = og["og:title"]
            if not meta["description"] and "og:description" in og:
                meta["description"] = og["og:description"]

            # Extract visible text snippet (first 500 chars)
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.decompose()
            visible = " ".join(soup.stripped_strings)
            meta["visible_text_snippet"] = visible[:500] if visible else None

        except Exception as parse_err:
            logger.debug(f"Metadata extraction error for '{base_url}': {parse_err}")

        return meta

    async def investigate_page(
        self,
        session: AsyncSession,
        case_id: uuid.UUID,
        organization_id: uuid.UUID,
        target_url: str,
        search_result_id: uuid.UUID | None = None,
        check_robots: bool = True,
    ) -> PageInvestigationResult:
        """Execute complete page investigation, metadata extraction, and DB record persistence."""
        is_social, platform_name = self.identify_social_platform(target_url)

        # 1. Fetch page through rendering fallback chain
        render_res: RenderedPageResult = await rendering_fallback_service.fetch_page(
            target_url,
            check_robots=check_robots,
        )

        final_url = render_res.final_url or target_url
        crawl_status = render_res.crawl_status

        # 2. Extract metadata if content is available
        meta_dict = self.extract_metadata_from_html(render_res.content_html, final_url)

        # 3. Extract public candidate images
        candidate_images: list[ExtractedImageCandidate] = []
        if render_res.content_html and crawl_status == CrawlStatus.SUCCESS:
            candidate_images = public_image_extractor.extract_from_html(
                render_res.content_html,
                base_url=final_url,
                max_images=settings.MAX_IMAGES_PER_PAGE,
            )

        if not candidate_images and crawl_status == CrawlStatus.SUCCESS and not meta_dict.get("title"):
            crawl_status = CrawlStatus.NO_PUBLIC_CONTENT

        # 4. Construct and persist PageInvestigation model
        page_inv = PageInvestigation(
            case_id=case_id,
            organization_id=organization_id,
            search_result_id=search_result_id,
            original_discovery_url=target_url,
            final_fetched_url=final_url,
            canonical_url=meta_dict.get("canonical"),
            http_status=render_res.status_code,
            fetch_method=render_res.fetch_method,
            fetch_provider=render_res.fetch_provider,
            page_title=meta_dict.get("title"),
            meta_description=meta_dict.get("description"),
            opengraph_json=meta_dict.get("opengraph", {}),
            twitter_json=meta_dict.get("twitter", {}),
            visible_text_snippet=meta_dict.get("visible_text_snippet"),
            extracted_images_count=len(candidate_images),
            crawl_status=crawl_status,
            error_category=render_res.error_category,
            duration_ms=render_res.duration_ms,
        )

        session.add(page_inv)
        await session.flush()

        return PageInvestigationResult(
            page_investigation=page_inv,
            candidate_image_urls=candidate_images,
            is_social_platform=is_social,
            platform_name=platform_name,
        )


page_investigation_service = PageInvestigationService()
