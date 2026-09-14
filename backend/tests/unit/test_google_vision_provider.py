"""Unit tests for Google Cloud Vision Web Detection Provider."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.services.provider_orchestration_service import (
    GoogleVisionWebDetectionProvider,
    NormalizedDiscoveryResult,
    ProviderOptions,
    ProviderStatus,
)


@pytest.fixture
def sample_web_detection_protobuf():
    """Mock protobuf response object mimicking google.cloud.vision.types.WebDetection."""
    mock_full = MagicMock()
    mock_full.url = "https://example.org/images/photo_full.jpg"

    mock_partial = MagicMock()
    mock_partial.url = "https://cdn.example.net/media/photo_crop.png"

    mock_page = MagicMock()
    mock_page.url = "https://news.example.com/article/123"
    mock_page.page_title = "Breaking News Story — Verified Press"
    mock_page.score = 0.92
    mock_page_full = MagicMock()
    mock_page_full.url = "https://news.example.com/assets/img.jpg"
    mock_page.full_matching_images = [mock_page_full]
    mock_page.partial_matching_images = []

    mock_sim = MagicMock()
    mock_sim.url = "https://social.example.org/user/pic.jpg"

    mock_entity = MagicMock()
    mock_entity.entity_id = "/m/0199g"
    mock_entity.description = "Cybersecurity"
    mock_entity.score = 0.89

    mock_best_guess = MagicMock()
    mock_best_guess.label = "Executive Portrait Headshot"

    mock_web = MagicMock()
    mock_web.full_matching_images = [mock_full]
    mock_web.partial_matching_images = [mock_partial]
    mock_web.pages_with_matching_images = [mock_page]
    mock_web.visually_similar_images = [mock_sim]
    mock_web.web_entities = [mock_entity]
    mock_web.best_guess_labels = [mock_best_guess]

    return mock_web


def test_provider_status_without_credentials():
    """Verify provider returns NOT_CONFIGURED when neither ADC nor API key is available."""
    provider = GoogleVisionWebDetectionProvider(api_key=None)
    with patch.object(provider, "_get_client", return_value=None):
        assert provider.get_status() == ProviderStatus.NOT_CONFIGURED


def test_provider_status_with_adc_client():
    """Verify provider returns READY when ADC client initializes successfully."""
    provider = GoogleVisionWebDetectionProvider(api_key=None)
    mock_client = MagicMock()
    with patch.object(provider, "_get_client", return_value=mock_client):
        assert provider.get_status() == ProviderStatus.READY


def test_provider_status_with_api_key():
    """Verify provider returns READY when API key is configured."""
    provider = GoogleVisionWebDetectionProvider(api_key="AIzaSyTestKey_12345")
    assert provider.get_status() == ProviderStatus.READY


def test_provider_circuit_breaker_tripping():
    """Verify circuit breaker trips to DEGRADED after consecutive failures."""
    provider = GoogleVisionWebDetectionProvider(api_key="AIzaSyTestKey_12345")
    mock_client = MagicMock()
    with patch.object(provider, "_get_client", return_value=mock_client):
        assert provider.get_status() == ProviderStatus.READY

        provider.circuit_breaker.record_failure()
        provider.circuit_breaker.record_failure()
        assert provider.get_status() == ProviderStatus.READY

        # 3rd failure trips breaker
        provider.circuit_breaker.record_failure()
        assert provider.circuit_breaker.state == "OPEN"
        assert provider.get_status() == ProviderStatus.DEGRADED

        # Recovery reset
        provider.circuit_breaker.record_success()
        assert provider.circuit_breaker.state == "CLOSED"
        assert provider.get_status() == ProviderStatus.READY


def test_normalization_of_vision_response(sample_web_detection_protobuf):
    """Verify normalization extracts all matching types, entities, and labels."""
    provider = GoogleVisionWebDetectionProvider()
    results = provider._parse_vision_response(
        sample_web_detection_protobuf,
        ProviderOptions(include_similar=True),
    )

    assert len(results) == 4

    # 1. Full match
    full = next(r for r in results if r.provider_raw_ref == "full_matching_images")
    assert full.source_url == "https://example.org/images/photo_full.jpg"
    assert full.domain == "example.org"
    assert full.provider_score == 1.0
    assert full.metadata["match_type"] == "FULL_MATCH"
    assert "best_guess_labels" in full.metadata
    assert full.metadata["best_guess_labels"] == ["Executive Portrait Headshot"]

    # 2. Partial match
    part = next(r for r in results if r.provider_raw_ref == "partial_matching_images")
    assert part.source_url == "https://cdn.example.net/media/photo_crop.png"
    assert part.domain == "cdn.example.net"
    assert part.metadata["match_type"] == "PARTIAL_MATCH"

    # 3. Page match
    page = next(r for r in results if r.provider_raw_ref == "pages_with_matching_images")
    assert page.page_url == "https://news.example.com/article/123"
    assert page.image_url == "https://news.example.com/assets/img.jpg"
    assert page.page_title == "Breaking News Story — Verified Press"
    assert page.metadata["match_type"] == "PAGE_MATCH"

    # 4. Visually similar
    sim = next(r for r in results if r.provider_raw_ref == "visually_similar_images")
    assert sim.source_url == "https://social.example.org/user/pic.jpg"
    assert sim.metadata["match_type"] == "VISUALLY_SIMILAR"


def test_empty_vision_response_handling():
    """Verify empty web detection payload returns empty list without raising."""
    provider = GoogleVisionWebDetectionProvider()
    results = provider._parse_vision_response(None, ProviderOptions())
    assert results == []


@pytest.mark.asyncio
async def test_live_discover_call_flow(sample_web_detection_protobuf):
    """Verify discover async method dispatches client call and normalizes output."""
    provider = GoogleVisionWebDetectionProvider(api_key=None)

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.error.message = ""
    mock_resp.web_detection = sample_web_detection_protobuf
    mock_client.web_detection.return_value = mock_resp

    with patch.object(provider, "_get_client", return_value=mock_client):
        results = await provider.discover(
            image_bytes=b"fake_raw_png_bytes_123",
            image_url=None,
            options=ProviderOptions(max_results=10),
        )

        assert len(results) == 4
        assert any(r.domain == "example.org" for r in results)
        assert provider.circuit_breaker.state == "CLOSED"
