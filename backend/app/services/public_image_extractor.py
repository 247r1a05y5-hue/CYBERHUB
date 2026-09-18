"""Public Image Extractor for Web Page Investigation.

Extracts candidate images from:
- img[src]
- img[srcset] & picture/source[srcset] (extracts highest resolution variant)
- meta[property="og:image"] & meta[name="og:image"]
- meta[name="twitter:image"] & meta[property="twitter:image"]
- JSON-LD structured schema image fields

Security & Hygiene:
- Resolves relative and protocol-relative URLs against final_fetched_url
- Rejects data: URIs, javascript: schemes, SVG icons, and tracking pixels
- Pre-download deduplication
- Enforces MAX_IMAGES_PER_PAGE limit
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

DISALLOWED_IMAGE_EXTENSIONS = {".svg", ".ico", ".gif", ".cur"}
TRACKING_PIXEL_KEYWORDS = {"pixel", "tracker", "beacon", "analytics", "spacer", "1x1", "1-pixel"}


@dataclass(frozen=True)
class ExtractedImageCandidate:
    """Discovered candidate image URL with extraction source context."""
    url: str
    source_tag: str  # "img_src", "srcset", "og:image", "twitter:image", "json_ld"
    alt_text: str | None = None
    width_hint: int | None = None
    height_hint: int | None = None


class PublicImageExtractor:
    """Extracts and sanitizes image URLs from webpage HTML."""

    @classmethod
    def resolve_url(cls, raw_url: str, base_url: str) -> str | None:
        """Sanitize and resolve relative/protocol-relative URL against base_url."""
        if not raw_url or not isinstance(raw_url, str):
            return None

        clean_raw = raw_url.strip()
        if clean_raw.startswith("data:") or clean_raw.startswith("javascript:"):
            return None

        try:
            resolved = urllib.parse.urljoin(base_url, clean_raw)
            parsed = urllib.parse.urlparse(resolved)
            if parsed.scheme.lower() not in ("http", "https"):
                return None
            if not parsed.hostname:
                return None

            # Remove hash anchors
            resolved = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                "",  # strip fragment
            ))
            return resolved
        except Exception:
            return None

    @classmethod
    def is_likely_tracking_pixel(cls, url: str, alt: str | None = None) -> bool:
        """Filter out tracking pixels and placeholder micro-icons."""
        url_lower = url.lower()
        alt_lower = (alt or "").lower()

        for kw in TRACKING_PIXEL_KEYWORDS:
            if kw in url_lower or kw in alt_lower:
                return True

        # Check for disallowed non-photographic icon extensions
        parsed = urllib.parse.urlparse(url_lower)
        for ext in DISALLOWED_IMAGE_EXTENSIONS:
            if parsed.path.endswith(ext):
                return True

        return False

    @classmethod
    def parse_srcset(cls, srcset_val: str, base_url: str) -> list[str]:
        """Parse srcset attribute and return candidate URLs (highest resolution first)."""
        candidates: list[tuple[str, float]] = []
        entries = re.split(r",\s*(?=[^\s]+)", srcset_val.strip())

        for entry in entries:
            parts = entry.strip().split()
            if not parts:
                continue
            cand_url = parts[0]
            resolved = cls.resolve_url(cand_url, base_url)
            if not resolved or cls.is_likely_tracking_pixel(resolved):
                continue

            # Parse descriptor (e.g. '2x' or '1200w')
            scale = 1.0
            if len(parts) > 1:
                desc = parts[1].lower()
                if desc.endswith("w"):
                    try:
                        scale = float(desc[:-1])
                    except ValueError:
                        scale = 1.0
                elif desc.endswith("x"):
                    try:
                        scale = float(desc[:-1]) * 1000.0
                    except ValueError:
                        scale = 1.0

            candidates.append((resolved, scale))

        # Sort descending by resolution descriptor
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in candidates]

    @classmethod
    def extract_from_html(
        cls,
        html_content: str | bytes,
        base_url: str,
        max_images: int | None = None,
    ) -> list[ExtractedImageCandidate]:
        """Extract deduplicated candidate images from HTML content."""
        max_limit = max_images or getattr(settings, "MAX_IMAGES_PER_PAGE", 15)
        extracted: list[ExtractedImageCandidate] = []
        seen_urls: set[str] = set()

        if isinstance(html_content, bytes):
            try:
                text_html = html_content.decode("utf-8", errors="replace")
            except Exception:
                text_html = str(html_content)
        else:
            text_html = html_content

        def add_candidate(url: str | None, source: str, alt: str | None = None, w: int | None = None, h: int | None = None) -> None:
            if not url or len(extracted) >= max_limit:
                return
            resolved = cls.resolve_url(url, base_url)
            if not resolved or resolved in seen_urls or cls.is_likely_tracking_pixel(resolved, alt):
                return
            seen_urls.add(resolved)
            extracted.append(
                ExtractedImageCandidate(
                    url=resolved,
                    source_tag=source,
                    alt_text=alt.strip() if alt else None,
                    width_hint=w,
                    height_hint=h,
                )
            )

        # 1. Try BeautifulSoup parser first
        soup = None
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text_html, "html.parser")
        except ImportError:
            soup = None

        if soup is not None:
            # 1a. OpenGraph meta tags
            for og_tag in soup.find_all("meta", property=re.compile(r"^og:image", re.I)):
                add_candidate(og_tag.get("content"), "og:image")

            # 1b. Twitter card meta tags
            for tw_tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:image", re.I)}):
                add_candidate(tw_tag.get("content"), "twitter:image")

            # 1c. JSON-LD Schema images
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    cls._extract_jsonld_images(data, add_candidate)
                except Exception:
                    pass

            # 1d. Picture / Source srcset
            for picture in soup.find_all("picture"):
                for source in picture.find_all("source"):
                    srcset = source.get("srcset")
                    if srcset:
                        for sc_url in cls.parse_srcset(srcset, base_url):
                            add_candidate(sc_url, "picture_srcset")

            # 1e. Standard img tags (srcset & src)
            for img in soup.find_all("img"):
                alt = img.get("alt")
                w_hint = None
                h_hint = None
                try:
                    if img.get("width"):
                        w_hint = int(img.get("width"))
                    if img.get("height"):
                        h_hint = int(img.get("height"))
                except ValueError:
                    pass

                # Ignore images explicitly styled/sized as tiny trackers
                if (w_hint is not None and w_hint < 16) or (h_hint is not None and h_hint < 16):
                    continue

                if img.get("srcset"):
                    for sc_url in cls.parse_srcset(img.get("srcset"), base_url):
                        add_candidate(sc_url, "img_srcset", alt, w_hint, h_hint)

                if img.get("src"):
                    add_candidate(img.get("src"), "img_src", alt, w_hint, h_hint)

        else:
            # Fallback regex extraction if BeautifulSoup is not installed
            # OpenGraph
            for m in re.finditer(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', text_html, re.I):
                add_candidate(m.group(1), "og:image")
            # Twitter
            for m in re.finditer(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', text_html, re.I):
                add_candidate(m.group(1), "twitter:image")
            # Standard img src
            for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', text_html, re.I):
                add_candidate(m.group(1), "img_src")

        return extracted

    @classmethod
    def _extract_jsonld_images(cls, data: Any, callback: Any) -> None:
        """Recursive helper to extract images from JSON-LD schema objects."""
        if isinstance(data, dict):
            img_val = data.get("image") or data.get("thumbnailUrl") or data.get("primaryImageOfPage")
            if isinstance(img_val, str):
                callback(img_val, "json_ld")
            elif isinstance(img_val, list):
                for item in img_val:
                    if isinstance(item, str):
                        callback(item, "json_ld")
                    elif isinstance(item, dict) and "url" in item:
                        callback(item["url"], "json_ld")
            elif isinstance(img_val, dict) and "url" in img_val:
                callback(img_val["url"], "json_ld")

            for v in data.values():
                cls._extract_jsonld_images(v, callback)
        elif isinstance(data, list):
            for item in data:
                cls._extract_jsonld_images(item, callback)


public_image_extractor = PublicImageExtractor()
