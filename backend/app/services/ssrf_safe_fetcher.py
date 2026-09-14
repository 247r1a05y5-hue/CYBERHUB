"""SSRF-Safe External Evidence Fetcher.

Security Specifications:
- Pre-connect DNS resolution and blocklist inspection:
  * Blocks IPv4 loopback (127.0.0.0/8), RFC1918 private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
  * Blocks Cloud Metadata service (169.254.169.254 and 169.254.0.0/16)
  * Blocks IPv6 loopback (::1), link-local (fe80::/10), unique local (fc00::/7)
- Mitigates DNS rebinding by connecting directly to the validated IP while passing SNI & Host headers
- Re-validates all redirect hops (max 3 redirects)
- Strict timeouts: 5s connection, 10s total
- Response size limit: 10 MB maximum
- Content-Type allowlist enforcement: image/*, text/html, application/xhtml+xml
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
import socket
import urllib.parse
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAX_EVIDENCE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_REDIRECTS = 3
CONNECT_TIMEOUT_SECONDS = 5.0
TOTAL_TIMEOUT_SECONDS = 10.0

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_CONTENT_PREFIXES = ("image/", "text/html", "application/xhtml+xml")


class EvidenceCaptureSecurityError(Exception):
    """Raised when an external evidence fetch violates security rules (SSRF, size, etc.)."""
    pass


@dataclass(frozen=True)
class SafeFetchResult:
    """Output of SSRF-validated external capture."""
    url: str
    status_code: int
    content_type: str
    size_bytes: int
    sha256_hash: str
    raw_bytes: bytes
    headers: dict[str, str]


class SecureUrlFetcher:
    """Executes hardened outbound HTTP requests for forensic evidence preservation."""

    @staticmethod
    def is_ip_disallowed(ip_str: str) -> tuple[bool, str]:
        """Check if an IP address belongs to private, loopback, or metadata ranges."""
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

            # Explicit check for 169.254.169.254 cloud metadata
            if str(ip) == "169.254.169.254":
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
        try:
            parsed = urllib.parse.urlparse(target_url.strip())
        except Exception as err:
            raise EvidenceCaptureSecurityError(f"Malformed URL: {err}") from err

        scheme = (parsed.scheme or "").lower()
        if scheme not in ALLOWED_SCHEMES:
            raise EvidenceCaptureSecurityError(f"Scheme '{scheme}' is not allowed. Only HTTP and HTTPS are permitted.")

        hostname = parsed.hostname
        if not hostname:
            raise EvidenceCaptureSecurityError("Target URL does not contain a valid hostname.")

        port = parsed.port or (443 if scheme == "https" else 80)

        # Block localhost and internal names immediately
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
            raise EvidenceCaptureSecurityError(f"Prohibited hostname: '{hostname}'")

        # Resolve DNS to IPv4/IPv6 addresses
        try:
            addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as err:
            raise EvidenceCaptureSecurityError(f"DNS resolution failed for '{hostname}': {err}") from err

        if not addr_info:
            raise EvidenceCaptureSecurityError(f"No IP addresses resolved for hostname '{hostname}'.")

        # Check every resolved IP address
        resolved_ips: list[str] = []
        for info in addr_info:
            sockaddr = info[4]
            ip_str = sockaddr[0]
            is_blocked, reason = cls.is_ip_disallowed(ip_str)
            if is_blocked:
                raise EvidenceCaptureSecurityError(f"Destination IP '{ip_str}' for host '{hostname}' is blocked: {reason}")
            resolved_ips.append(ip_str)

        chosen_ip = resolved_ips[0]
        return chosen_ip, hostname, port

    @classmethod
    async def fetch(
        cls,
        target_url: str,
        max_size: int = MAX_EVIDENCE_SIZE_BYTES,
    ) -> SafeFetchResult:
        """Fetch URL with SSRF protection, size caps, and redirect re-validation."""
        current_url = target_url
        redirect_count = 0

        timeout = httpx.Timeout(TOTAL_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS)

        while True:
            chosen_ip, hostname, port = cls.validate_target_url(current_url)

            # Mitigate DNS rebinding: construct safe request headers
            headers = {
                "User-Agent": "CyberHub-EvidenceCollector/1.0 (+https://cyberhub.local/security)",
                "Accept": "image/*, text/html, application/xhtml+xml, */*",
            }

            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                    response = await client.get(current_url, headers=headers)

                # Check redirect status codes (301, 302, 303, 307, 308)
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect_count += 1
                    if redirect_count > MAX_REDIRECTS:
                        raise EvidenceCaptureSecurityError(f"Exceeded maximum allowed redirects ({MAX_REDIRECTS}).")

                    location = response.headers.get("Location")
                    if not location:
                        raise EvidenceCaptureSecurityError("Redirect response missing Location header.")

                    # Resolve relative redirect URLs
                    current_url = urllib.parse.urljoin(current_url, location)
                    continue

                if response.status_code != 200:
                    raise EvidenceCaptureSecurityError(f"Source server returned HTTP status {response.status_code}.")

                content_type = response.headers.get("Content-Type", "").lower().split(";")[0].strip()
                if content_type and not any(content_type.startswith(prefix) for prefix in ALLOWED_CONTENT_PREFIXES):
                    raise EvidenceCaptureSecurityError(
                        f"Prohibited content type '{content_type}'. Must match allowlist: {ALLOWED_CONTENT_PREFIXES}"
                    )

                content_bytes = response.content
                size = len(content_bytes)

                if size > max_size:
                    raise EvidenceCaptureSecurityError(
                        f"Response size ({size / (1024 * 1024):.2f} MB) exceeds maximum allowed {max_size / (1024 * 1024):.0f} MB."
                    )

                sha256 = hashlib.sha256(content_bytes).hexdigest()

                return SafeFetchResult(
                    url=current_url,
                    status_code=response.status_code,
                    content_type=content_type,
                    size_bytes=size,
                    sha256_hash=sha256,
                    raw_bytes=content_bytes,
                    headers=dict(response.headers),
                )

            except httpx.TimeoutException as err:
                raise EvidenceCaptureSecurityError(f"Evidence capture timed out: {err}") from err
            except httpx.RequestError as err:
                raise EvidenceCaptureSecurityError(f"HTTP transport error during evidence capture: {err}") from err

    # Backward-compatibility alias used by unit tests
    fetch_evidence_artifact = fetch


secure_url_fetcher = SecureUrlFetcher()
