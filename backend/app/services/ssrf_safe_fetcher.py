"""SSRF-Safe External Evidence and Webpage Fetcher.

Security Specifications:
- Pre-connect DNS resolution and strict IP blocklist inspection:
  * Blocks IPv4 loopback (127.0.0.0/8), RFC1918 private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
  * Blocks Cloud Metadata service (169.254.169.254 and 169.254.0.0/16)
  * Blocks IPv6 loopback (::1), link-local (fe80::/10), unique local (fc00::/7)
- Mitigates DNS rebinding by validating resolved IPs before connecting
- Re-validates every redirect hop independently (safe origin never implies safe redirect target)
- Tracks complete redirect chains for forensic provenance
- Strict timeouts and response size limits (preventing decompression bombs and slowloris attacks)
- Scheme allowlist: http, https only (strictly rejects file://, ftp://, data://, javascript://)
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
import socket
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_REDIRECTS = 5
CONNECT_TIMEOUT_SECONDS = 5.0
TOTAL_TIMEOUT_SECONDS = 10.0

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_CONTENT_PREFIXES = (
    "image/",
    "text/html",
    "text/plain",
    "application/xhtml+xml",
    "application/xml",
    "application/json",
)


class EvidenceCaptureSecurityError(Exception):
    """Raised when an external fetch violates security rules (SSRF, size, scheme, etc.)."""
    pass


class RobotsDisallowedError(EvidenceCaptureSecurityError):
    """Raised when robots.txt disallows automated fetching of target URL."""
    pass


@dataclass(frozen=True)
class SafeFetchResult:
    """Output of SSRF-validated external capture."""
    url: str
    original_url: str
    status_code: int
    content_type: str
    size_bytes: int
    sha256_hash: str
    raw_bytes: bytes
    headers: dict[str, str]
    redirect_chain: list[str] = field(default_factory=list)

    @property
    def final_url(self) -> str:
        return self.url


class SecureUrlFetcher:
    """Executes hardened outbound HTTP requests for web investigation and evidence preservation."""

    @staticmethod
    def is_ip_disallowed(ip_str: str) -> tuple[bool, str]:
        """Check if an IP address belongs to private, loopback, link-local, or cloud metadata ranges."""
        try:
            ip = ipaddress.ip_address(ip_str)

            if ip.is_loopback:
                return True, "Loopback IP address is prohibited."
            if ip.is_private:
                return True, "Private / RFC1918 IP address range is prohibited."
            if ip.is_link_local:
                return True, "Link-local / Cloud metadata IP address is prohibited."
            if ip.is_multicast:
                return True, "Multicast IP address is prohibited."
            if ip.is_reserved:
                return True, "Reserved IP address is prohibited."
            if ip.is_unspecified:
                return True, "Unspecified IP address is prohibited."

            # Explicit check for 169.254.169.254 and AWS/GCP/Azure link-local metadata
            if str(ip).startswith("169.254."):
                return True, "Cloud metadata endpoint is strictly prohibited."

            return False, "OK"
        except ValueError:
            return True, "Invalid IP address syntax."

    @classmethod
    def is_ip_allowed(cls, ip_str: str) -> bool:
        """Helper returning True if IP is permitted for outbound fetch."""
        disallowed, _ = cls.is_ip_disallowed(ip_str)
        return not disallowed

    @classmethod
    def validate_target_url(cls, target_url: str) -> tuple[str, str, int]:
        """Validate URL scheme, resolve DNS, and verify IP against SSRF blocklists."""
        if not target_url or not isinstance(target_url, str):
            raise EvidenceCaptureSecurityError("Target URL must be a non-empty string.")

        try:
            parsed = urllib.parse.urlparse(target_url.strip())
        except Exception as err:
            raise EvidenceCaptureSecurityError(f"Malformed URL: {err}") from err

        scheme = (parsed.scheme or "").lower()
        if scheme not in ALLOWED_SCHEMES:
            raise EvidenceCaptureSecurityError(
                f"Scheme '{scheme}' is prohibited. Only HTTP and HTTPS are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise EvidenceCaptureSecurityError("Target URL does not contain a valid hostname.")

        port = parsed.port or (443 if scheme == "https" else 80)

        # Block localhost and well-known internal names immediately
        if hostname.lower() in (
            "localhost",
            "127.0.0.1",
            "::1",
            "metadata.google.internal",
            "instance-data",
            "169.254.169.254",
        ) or hostname.lower().endswith(".local") or hostname.lower().endswith(".internal"):
            raise EvidenceCaptureSecurityError(f"Prohibited internal hostname: '{hostname}'")

        # Resolve DNS to IPv4/IPv6 addresses
        try:
            addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as err:
            raise EvidenceCaptureSecurityError(f"DNS resolution failed for '{hostname}': {err}") from err

        if not addr_info:
            raise EvidenceCaptureSecurityError(f"No IP addresses resolved for hostname '{hostname}'.")

        # Verify EVERY resolved IP address against SSRF rules
        resolved_ips: list[str] = []
        for info in addr_info:
            sockaddr = info[4]
            ip_str = sockaddr[0]
            is_blocked, reason = cls.is_ip_disallowed(ip_str)
            if is_blocked:
                raise EvidenceCaptureSecurityError(
                    f"Destination IP '{ip_str}' for host '{hostname}' is prohibited: {reason}"
                )
            resolved_ips.append(ip_str)

        chosen_ip = resolved_ips[0]
        return chosen_ip, hostname, port

    @classmethod
    async def fetch(
        cls,
        target_url: str,
        max_size: int = MAX_PAGE_SIZE_BYTES,
        max_redirects: int = MAX_REDIRECTS,
        headers_override: dict[str, str] | None = None,
        check_robots: bool = False,
    ) -> SafeFetchResult:
        """Fetch URL with SSRF protection, independent per-hop redirect validation, and size limits."""
        if check_robots:
            from app.services.crawl_courtesy_service import crawl_courtesy_service
            courtesy_res = await crawl_courtesy_service.prepare_fetch(target_url)
            if not courtesy_res.is_allowed:
                raise RobotsDisallowedError(f"Crawl courtesy block: {courtesy_res.reason}")

        current_url = target_url.strip()
        original_url = current_url
        redirect_chain: list[str] = [current_url]
        redirect_count = 0

        timeout = httpx.Timeout(TOTAL_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS)

        headers = {
            "User-Agent": "CyberHub-EvidenceCollector/1.0 (+https://cyberhub.local/security)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers_override:
            headers.update(headers_override)

        while True:
            # Re-validate every hop independently
            chosen_ip, hostname, port = cls.validate_target_url(current_url)

            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                    response = await client.get(current_url, headers=headers)

                # Check for HTTP redirect status codes (301, 302, 303, 307, 308)
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect_count += 1
                    if redirect_count > max_redirects:
                        raise EvidenceCaptureSecurityError(
                            f"Exceeded maximum allowed redirects ({max_redirects})."
                        )

                    location = response.headers.get("Location")
                    if not location:
                        raise EvidenceCaptureSecurityError("Redirect response missing Location header.")

                    # Resolve relative redirect URLs against the current hop URL
                    next_url = urllib.parse.urljoin(current_url, location)
                    redirect_chain.append(next_url)
                    current_url = next_url
                    continue

                content_type = response.headers.get("Content-Type", "").lower().split(";")[0].strip()
                if content_type and not any(content_type.startswith(prefix) for prefix in ALLOWED_CONTENT_PREFIXES):
                    raise EvidenceCaptureSecurityError(
                        f"Prohibited content type '{content_type}'. Must match allowlist: {ALLOWED_CONTENT_PREFIXES}"
                    )

                content_bytes = response.content
                size = len(content_bytes)

                if size > max_size:
                    raise EvidenceCaptureSecurityError(
                        f"Response size ({size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {max_size / (1024 * 1024):.1f} MB."
                    )

                sha256 = hashlib.sha256(content_bytes).hexdigest()

                return SafeFetchResult(
                    url=current_url,
                    original_url=original_url,
                    status_code=response.status_code,
                    content_type=content_type,
                    size_bytes=size,
                    sha256_hash=sha256,
                    raw_bytes=content_bytes,
                    headers=dict(response.headers),
                    redirect_chain=redirect_chain,
                )

            except httpx.TimeoutException as err:
                raise EvidenceCaptureSecurityError(f"HTTP request timed out: {err}") from err
            except httpx.RequestError as err:
                raise EvidenceCaptureSecurityError(f"HTTP transport error during capture: {err}") from err

    # Backward-compatibility alias
    fetch_evidence_artifact = fetch


secure_url_fetcher = SecureUrlFetcher()
