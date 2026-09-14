"""Test SSRF protection on evidence URLs."""
import pytest
from app.core.ssrf import is_safe_url, validate_outbound_url
from app.core.exceptions import ValidationError


def test_ssrf_blocks_private_and_loopback_ips():
    assert is_safe_url("http://127.0.0.1:8000/secret") is False
    assert is_safe_url("http://localhost/admin") is False
    assert is_safe_url("http://10.0.0.1/metadata") is False
    assert is_safe_url("http://192.168.1.1/router") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data") is False


def test_ssrf_allows_public_domains():
    assert is_safe_url("https://example.com/profile.png") is True
    assert is_safe_url("https://images.unsplash.com/photo-123") is True


def test_validate_outbound_url_raises_validation_error():
    with pytest.raises(ValidationError):
        validate_outbound_url("http://127.0.0.1:8000/internal")
