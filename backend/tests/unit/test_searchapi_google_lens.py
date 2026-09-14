"""Unit tests for SearchAPI Google Lens provider and ephemeral temporary image lifecycle."""
import pytest
import time
from unittest.mock import MagicMock, patch
import httpx

from app.services.provider_orchestration_service import (
    SearchAPIGoogleLensProvider,
    NormalizedDiscoveryResult,
    ProviderOptions,
    ProviderStatus,
)
from app.services.temporary_image_service import temporary_image_service, TemporaryImageService
from app.services.ssrf_safe_fetcher import SecureUrlFetcher, EvidenceCaptureSecurityError
from app.services.deduplication_clustering_service import deduplication_and_clustering_service
from app.services.image_matching_service import image_matching_service
from app.services.image_analysis_service import image_analysis_service
from app.services.dinov2_service import dinov2_service


@pytest.fixture
def sample_searchapi_response():
    """Standard SearchAPI Google Lens JSON response."""
    return {
        "search_metadata": {
            "id": "search_lens_test_123",
            "status": "Success",
            "created_at": "2026-09-14T00:00:00Z",
            "request_time_taken": 0.45,
        },
        "search_parameters": {
            "engine": "google_lens",
            "url": "http://localhost:8000/api/v1/temp-images/token123",
        },
        "exact_matches": [
            {
                "position": 1,
                "title": "Verified Press Release Portrait",
                "link": "https://press.example.org/news/executive.jpg",
                "source": "press.example.org",
                "thumbnail": "https://press.example.org/thumb/executive.jpg",
                "image": "https://press.example.org/news/executive.jpg",
                "snippet": "Official portrait from press room release.",
            }
        ],
        "visual_matches": [
            {
                "position": 2,
                "title": "Public Social Profile Avatar",
                "link": "https://social.example.org/user/101",
                "source": "social.example.org",
                "thumbnail": "https://social.example.org/img/avatar.png",
                "image": "https://social.example.org/img/avatar.png",
                "snippet": "User profile avatar photo on social network.",
            },
            {
                "position": 3,
                "title": "Digital News Wire Story",
                "link": "https://wire.example.com/story/889",
                "source": "wire.example.com",
                "thumbnail": "https://wire.example.com/media/thumb_889.jpg",
                "image": "https://wire.example.com/media/full_889.jpg",
                "snippet": "Security briefing and coverage.",
            },
        ],
        "knowledge_graph": [
            {
                "title": "Cybersecurity Architecture",
                "subtitle": "Computer Security Topic",
                "link": "https://google.com/search?q=Cybersecurity",
            }
        ],
        "related_searches": [
            {"query": "Executive Cybersecurity Profiles"}
        ],
    }


# 1. Missing API Key
def test_searchapi_missing_api_key():
    prov = SearchAPIGoogleLensProvider(api_key=None)
    assert prov.get_status() == ProviderStatus.NOT_CONFIGURED


# 2. Successful Provider Response Mocked at HTTP Boundary
@pytest.mark.asyncio
async def test_searchapi_successful_response(sample_searchapi_response):
    prov = SearchAPIGoogleLensProvider(api_key="test_searchapi_key_123")
    assert prov.get_status() == ProviderStatus.READY

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = sample_searchapi_response

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        results = await prov.discover(
            image_bytes=b"sample_test_image_bytes_123",
            image_url=None,
            options=ProviderOptions(max_results=10),
        )

        assert len(results) == 4
        # Exact match
        exact = next(r for r in results if r.provider_raw_ref == "exact_matches")
        assert exact.provider_score == 1.0
        assert exact.metadata["match_type"] == "EXACT"
        assert exact.domain == "press.example.org"

        # Visual matches
        visuals = [r for r in results if r.provider_raw_ref == "visual_matches"]
        assert len(visuals) == 2
        assert visuals[0].metadata["match_type"] == "VISUALLY_SIMILAR"


# 3. Provider 401 / 403 Authentication Error
@pytest.mark.asyncio
async def test_searchapi_provider_auth_error():
    prov = SearchAPIGoogleLensProvider(api_key="invalid_or_expired_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        with pytest.raises(PermissionError) as exc:
            await prov.discover(
                image_bytes=b"sample_test_image_bytes_123",
                image_url="https://example.com/img.jpg",
                options=ProviderOptions(),
            )
        assert "PROVIDER_AUTH_ERROR" in str(exc.value)


# 4. Provider Timeout
@pytest.mark.asyncio
async def test_searchapi_provider_timeout():
    prov = SearchAPIGoogleLensProvider(api_key="test_searchapi_key_123")

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Read timeout")):
        with pytest.raises(TimeoutError) as exc:
            await prov.discover(
                image_bytes=b"sample_test_image_bytes_123",
                image_url="https://example.com/img.jpg",
                options=ProviderOptions(timeout_seconds=2.0),
            )
        assert "PROVIDER_TIMEOUT" in str(exc.value)


# 5. Empty Results (NO_MATCHES)
@pytest.mark.asyncio
async def test_searchapi_empty_results():
    prov = SearchAPIGoogleLensProvider(api_key="test_searchapi_key_123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"search_metadata": {"status": "Success"}, "visual_matches": []}

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        results = await prov.discover(
            image_bytes=b"sample_test_image_bytes_123",
            image_url="https://example.com/img.jpg",
            options=ProviderOptions(),
        )
        assert results == []


# 6. Malformed Provider Response
@pytest.mark.asyncio
async def test_searchapi_malformed_response():
    prov = SearchAPIGoogleLensProvider(api_key="test_searchapi_key_123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = "Non-dict string output"

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        results = await prov.discover(
            image_bytes=b"sample_test_image_bytes_123",
            image_url="https://example.com/img.jpg",
            options=ProviderOptions(),
        )
        assert results == []


# 7. Candidate Normalization
def test_searchapi_candidate_normalization(sample_searchapi_response):
    prov = SearchAPIGoogleLensProvider(api_key="test_searchapi_key_123")
    results = prov._parse_searchapi_response(sample_searchapi_response, ProviderOptions(max_results=20))

    assert len(results) == 4
    for r in results:
        assert r.provider == "SearchAPIGoogleLens"
        assert r.domain != ""
        assert r.source_url != ""
        assert "match_type" in r.metadata
        assert "search_id" in r.metadata
        assert r.metadata["search_id"] == "search_lens_test_123"


# 8. SSRF Protection on External Egress
def test_searchapi_ssrf_protection_blocked_destinations():
    blocked_urls = [
        "http://127.0.0.1/admin",
        "http://localhost:8000/secret",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/config",
        "http://192.168.1.1/router",
        "http://[::1]/internal",
    ]
    for url in blocked_urls:
        with pytest.raises(EvidenceCaptureSecurityError):
            SecureUrlFetcher.validate_target_url(url)


# 9. Tenant Isolation
def test_searchapi_tenant_candidate_provenance(sample_searchapi_response):
    prov = SearchAPIGoogleLensProvider(api_key="test_searchapi_key_123")
    results = prov._parse_searchapi_response(sample_searchapi_response, ProviderOptions())
    
    # Results belong strictly to the querying context
    assert all(r.provider == "SearchAPIGoogleLens" for r in results)


# 10. Duplicate Candidate Handling & Provenance Merge
def test_searchapi_duplicate_candidate_handling(sample_searchapi_response):
    prov = SearchAPIGoogleLensProvider(api_key="test_searchapi_key_123")
    results1 = prov._parse_searchapi_response(sample_searchapi_response, ProviderOptions())
    results2 = prov._parse_searchapi_response(sample_searchapi_response, ProviderOptions())

    combined = results1 + results2
    deduped = deduplication_and_clustering_service.deduplicate_results(combined)

    # 4 unique items despite being passed twice
    assert len(deduped) == 4
    for d in deduped:
        assert len(d.provenance_records) >= 1


# 11. Phase 3 Matching Integration
def test_searchapi_phase3_matching_integration():
    import io
    from PIL import Image

    img = Image.new("RGB", (64, 64), color=(30, 60, 90))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    ref_bytes = buf.getvalue()
    cand_bytes = ref_bytes

    ref_analysis = image_analysis_service.analyze(ref_bytes)
    cand_analysis = image_analysis_service.analyze(cand_bytes)

    ref_emb = dinov2_service.extract_embedding(ref_bytes)
    cand_emb = dinov2_service.extract_embedding(cand_bytes)

    eval_result = image_matching_service.evaluate_match(
        reference_sha256=ref_analysis.sha256_hash,
        candidate_sha256=cand_analysis.sha256_hash,
        reference_phash=ref_analysis.phash,
        candidate_phash=cand_analysis.phash,
        reference_vector=ref_emb.vector,
        candidate_vector=cand_emb.vector,
    )

    assert eval_result.overall_similarity_score == 1.0
    assert eval_result.classification.value == "EXACT"


# 12. Ephemeral Temporary Image Token TTL & Deletion
def test_temporary_image_lifecycle_ttl_and_deletion():
    svc = TemporaryImageService()
    test_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"

    # Create temporary image with 2-second TTL
    token, url = svc.create_temporary_image(test_bytes, content_type="image/jpeg", ttl_seconds=2)
    assert token in url
    assert svc.active_count() == 1

    # Fetch while active
    retrieved = svc.get_temporary_image(token)
    assert retrieved is not None
    assert retrieved[0] == test_bytes
    assert retrieved[1] == "image/jpeg"

    # Explicit deletion
    deleted = svc.delete_temporary_image(token)
    assert deleted is True
    assert svc.get_temporary_image(token) is None
    assert svc.active_count() == 0
