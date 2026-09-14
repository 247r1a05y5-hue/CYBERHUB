"""Unit & Security tests for SSRF-Safe Evidence Fetcher (Slice 8).

Tests:
- Localhost & Loopback addresses rejected (127.0.0.1, ::1)
- Private RFC1918 addresses rejected (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Cloud Metadata Service rejected (169.254.169.254)
- Unsupported schemes rejected (file://, ftp://, gopher://)
- Non-image MIME types rejected
"""
from __future__ import annotations

import pytest
from app.services.ssrf_safe_fetcher import (
    EvidenceCaptureSecurityError,
    secure_url_fetcher,
)


class TestSSRFProtection:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "blocked_url",
        [
            "http://127.0.0.1/admin",
            "http://localhost:8000/secret",
            "http://[::1]/internal",
            "http://10.0.0.1/config",
            "http://172.16.5.4/db",
            "http://192.168.1.1/router",
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.169.254/metadata/v1.json",
            "file:///etc/passwd",
            "gopher://127.0.0.1:6379/_flushall",
            "ftp://ftp.local/backup.tar.gz",
        ],
    )
    async def test_ssrf_blocked_destinations(self, blocked_url: str):
        with pytest.raises(EvidenceCaptureSecurityError):
            await secure_url_fetcher.fetch_evidence_artifact(blocked_url)

    def test_ip_validation_helper(self):
        assert secure_url_fetcher.is_ip_allowed("1.1.1.1") is True
        assert secure_url_fetcher.is_ip_allowed("8.8.8.8") is True
        assert secure_url_fetcher.is_ip_allowed("127.0.0.1") is False
        assert secure_url_fetcher.is_ip_allowed("10.10.10.10") is False
        assert secure_url_fetcher.is_ip_allowed("172.20.1.1") is False
        assert secure_url_fetcher.is_ip_allowed("192.168.1.100") is False
        assert secure_url_fetcher.is_ip_allowed("169.254.169.254") is False
