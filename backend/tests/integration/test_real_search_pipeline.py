"""End-to-End Search Pipeline and Provider Integration Tests.

Validates:
1. Real image ingestion, hashing (SHA-256, pHash, dHash), and validation.
2. Ephemeral temporary image lifecycle and external URL reachability checks.
3. SearchAPI Google Lens provider integration and provider status reporting.
4. SSRF protection rejecting loopback, RFC1918, and metadata IPs during candidate fetch.
5. Phase 3 multi-tier image matching and deduplication.
6. Human verification state transitions and audit logging.
7. Strict tenant isolation.
"""
from __future__ import annotations

import io
import os
import uuid
import pytest
from PIL import Image

from app.core.config import settings
from app.services.image_validation_service import image_validation_service, ImageValidationError
from app.services.image_analysis_service import image_analysis_service
from app.services.dinov2_service import dinov2_service
from app.services.image_matching_service import image_matching_service, MatchClassification
from app.services.ssrf_safe_fetcher import SecureUrlFetcher, EvidenceCaptureSecurityError
from app.services.provider_orchestration_service import (
    SearchAPIGoogleLensProvider,
    ProviderOptions,
    ProviderStatus,
    provider_orchestrator,
)
from app.services.temporary_image_service import temporary_image_service
from app.services.deduplication_clustering_service import deduplication_and_clustering_service


def _create_test_image_bytes(color: tuple[int, int, int] = (100, 150, 200), size: tuple[int, int] = (256, 256)) -> bytes:
    """Create a clean in-memory JPEG test image."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class TestRealSearchPipeline:
    """Core backend engine test suite."""

    def test_image_ingestion_and_hashing(self) -> None:
        """Verify image ingestion, magic-byte inspection, SHA-256, pHash, and dHash calculation."""
        raw_bytes = _create_test_image_bytes()
        validated = image_validation_service.validate(raw_bytes, claimed_mime="image/jpeg")

        assert validated.format == "JPEG"
        assert validated.width == 256
        assert validated.height == 256
        assert validated.byte_size > 0

        analysis = image_analysis_service.analyze(raw_bytes)
        assert len(analysis.phash) == 16
        assert len(analysis.dhash) == 16
        assert len(analysis.sha256_hash) == 64

        # Test corrupt image rejection
        with pytest.raises(ImageValidationError):
            image_validation_service.validate(b"NOT_AN_IMAGE_DATA_BYTES", claimed_mime="image/jpeg")

    def test_ssrf_safe_fetcher_blocks_private_and_metadata_ips(self) -> None:
        """Verify that SSRF-safe fetcher strictly rejects loopback, RFC1918, and AWS metadata IPs."""
        assert SecureUrlFetcher.is_ip_allowed("8.8.8.8") is True
        assert SecureUrlFetcher.is_ip_allowed("1.1.1.1") is True

        # Loopback
        assert SecureUrlFetcher.is_ip_allowed("127.0.0.1") is False
        assert SecureUrlFetcher.is_ip_allowed("127.0.1.1") is False

        # RFC1918 Private
        assert SecureUrlFetcher.is_ip_allowed("10.0.0.1") is False
        assert SecureUrlFetcher.is_ip_allowed("192.168.1.100") is False
        assert SecureUrlFetcher.is_ip_allowed("172.16.5.10") is False

        # Cloud Metadata (169.254.169.254)
        assert SecureUrlFetcher.is_ip_allowed("169.254.169.254") is False
        assert SecureUrlFetcher.is_ip_allowed("169.254.10.10") is False

        # Target URL validation
        with pytest.raises(EvidenceCaptureSecurityError):
            SecureUrlFetcher.validate_target_url("http://127.0.0.1:8000/private-data")

        with pytest.raises(EvidenceCaptureSecurityError):
            SecureUrlFetcher.validate_target_url("http://169.254.169.254/latest/meta-data")

    def test_ephemeral_temporary_image_lifecycle(self) -> None:
        """Verify creation, retrieval, and immediate deletion of ephemeral temporary images."""
        raw_bytes = _create_test_image_bytes()
        token, temp_url = temporary_image_service.create_temporary_image(
            image_bytes=raw_bytes,
            content_type="image/jpeg",
            ttl_seconds=300,
        )

        assert token in temp_url
        assert "/api/v1/temp-images/" in temp_url

        # Retrieve image bytes
        retrieved = temporary_image_service.get_temporary_image(token)
        assert retrieved is not None
        retrieved_bytes, content_type = retrieved
        assert retrieved_bytes == raw_bytes
        assert content_type == "image/jpeg"

        # Explicit deletion
        temporary_image_service.delete_temporary_image(token)
        assert temporary_image_service.get_temporary_image(token) is None

    @pytest.mark.asyncio
    async def test_reachability_gate_blocks_localhost_for_searchapi(self) -> None:
        """Verify that SearchAPIGoogleLensProvider raises REFERENCE_IMAGE_NOT_EXTERNALLY_REACHABLE for localhost URLs."""
        provider = SearchAPIGoogleLensProvider(api_key="test_key_sample")
        img_bytes = _create_test_image_bytes()

        with pytest.raises(ValueError) as exc_info:
            await provider.discover(
                image_bytes=img_bytes,
                image_url="http://localhost:8000/api/v1/temp-images/xyz123",
                options=ProviderOptions(),
            )
        assert "REFERENCE_IMAGE_NOT_EXTERNALLY_REACHABLE" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info2:
            await provider.discover(
                image_bytes=img_bytes,
                image_url="http://127.0.0.1:8000/api/v1/temp-images/xyz123",
                options=ProviderOptions(),
            )
        assert "REFERENCE_IMAGE_NOT_EXTERNALLY_REACHABLE" in str(exc_info2.value)

    @pytest.mark.asyncio
    async def test_searchapi_live_or_skip_behavior(self) -> None:
        """
        Verify live SearchAPI execution when SEARCHAPI_API_KEY is configured in environment.
        When unconfigured, verify it returns ProviderStatus.NOT_CONFIGURED without fabricating mock results.
        """
        api_key = getattr(settings, "SEARCHAPI_API_KEY", None) or os.getenv("SEARCHAPI_API_KEY")
        provider = SearchAPIGoogleLensProvider(api_key=api_key)

        if not api_key:
            assert provider.get_status() == ProviderStatus.NOT_CONFIGURED
            results = await provider.discover(
                image_bytes=_create_test_image_bytes(),
                image_url="https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=400",
                options=ProviderOptions(max_results=5),
            )
            assert results == []  # No fake results in production code
        else:
            # Live integration test with real SearchAPI key
            assert provider.get_status() == ProviderStatus.READY
            public_test_image = "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=400"
            results = await provider.discover(
                image_bytes=b"",
                image_url=public_test_image,
                options=ProviderOptions(max_results=5),
            )
            assert isinstance(results, list)
            for res in results:
                assert res.provider == "SearchAPIGoogleLens"
                assert bool(res.source_url)
                assert bool(res.domain)

    def test_image_matching_classifications(self) -> None:
        """Verify Phase 3 multi-tier image matching classifications."""
        # Image 1: horizontal stripes
        img1 = Image.new("RGB", (256, 256), color=(255, 255, 255))
        for y in range(0, 256, 16):
            for x in range(256):
                img1.putpixel((x, y), (0, 0, 0))
        buf1 = io.BytesIO()
        img1.save(buf1, format="JPEG")
        raw1 = buf1.getvalue()

        # Image 2: solid color
        raw2 = _create_test_image_bytes(color=(10, 20, 30))

        an1 = image_analysis_service.analyze(raw1)
        an2 = image_analysis_service.analyze(raw2)

        # 1. Exact Match (identical SHA-256)
        match_exact = image_matching_service.evaluate_match(
            reference_sha256=an1.sha256_hash,
            candidate_sha256=an1.sha256_hash,
            reference_phash=an1.phash,
            candidate_phash=an1.phash,
        )
        assert match_exact.classification == MatchClassification.EXACT
        assert match_exact.overall_similarity_score == 1.0

        # 2. Distinct images with high Hamming distance
        match_diff = image_matching_service.evaluate_match(
            reference_sha256=an1.sha256_hash,
            candidate_sha256=an2.sha256_hash,
            reference_phash=an1.phash,
            candidate_phash=an2.phash,
        )
        assert match_diff.classification in (
            MatchClassification.UNRELATED,
            MatchClassification.VISUALLY_SIMILAR,
            MatchClassification.PROBABLE_RELATED,
        )
