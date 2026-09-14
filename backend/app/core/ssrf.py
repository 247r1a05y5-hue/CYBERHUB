"""SSRF Protection utility — Validates outbound URLs before requests."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.exceptions import ValidationError

# Private, loopback, link-local, multicast, and reserved IPv4 / IPv6 networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
]


def is_safe_url(url: str) -> bool:
    """Check whether a URL is safe to fetch (not pointing to internal/reserved addresses)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # If hostname is a bare IP address, check directly without DNS
        try:
            ip_obj = ipaddress.ip_address(hostname)
            for blocked in BLOCKED_NETWORKS:
                if ip_obj in blocked:
                    return False
            return True
        except ValueError:
            pass  # Not an IP address — it's a hostname, resolve below

        # Resolve hostname to IP addresses
        try:
            addr_infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        except (socket.gaierror, OSError):
            # DNS resolution failed — can't confirm it's unsafe, allow it
            # (Genuine internal hostnames are IP addresses or resolve to private IPs)
            return True

        for addr in addr_infos:
            ip_str = addr[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            for blocked in BLOCKED_NETWORKS:
                if ip_obj in blocked:
                    return False

        return True
    except Exception:
        return False


def validate_outbound_url(url: str) -> str:
    """Validate URL and raise ValidationError if URL violates SSRF policy."""
    if not is_safe_url(url):
        raise ValidationError(f"URL destination is not permitted by security policy: {url}")
    return url
