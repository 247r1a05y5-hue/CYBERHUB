"""Integration tests for SearchAPI Google Lens Web Discovery API."""
import io
import uuid
import pytest
from httpx import AsyncClient
from PIL import Image

from app.models.case import Case, CaseStatus
from app.models.user import User
from app.models.organization import Organization
from app.services.provider_orchestration_service import (
    NormalizedDiscoveryResult,
    provider_orchestrator,
)
from datetime import datetime, timezone
from unittest.mock import patch


def create_test_image_bytes() -> bytes:
    img = Image.new("RGB", (128, 128), color=(30, 80, 140))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
class TestSearchAPIWebSearchAPI:
    """End-to-end integration tests for SearchAPI Google Lens endpoint."""

    async def test_searchapi_web_search_full_flow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        # 1. Create Investigation
        case_res = await client.post(
            "/api/v1/investigations",
            json={"title": "SearchAPI Lens Case", "description": "Testing SearchAPI Google Lens integration"},
            headers=auth_headers,
        )
        assert case_res.status_code == 201, case_res.text
        inv_id = case_res.json()["id"]

        # 2. Attest Case
        att_res = await client.post(
            f"/api/v1/investigations/{inv_id}/attestation",
            json={
                "purpose": "AUTHORIZED_SECURITY_AUDIT",
                "authority_basis": "Incident Response #LENS-101",
                "attestation_text": "I hereby certify this investigation is authorized under company security policy.",
                "authorized_by_org": True,
                "data_handling_ack": True,
                "retention_policy_ack": True,
                "no_unauthorized_pii_ack": True,
            },
            headers=auth_headers,
        )
        assert att_res.status_code in (200, 201), att_res.text

        # 3. Upload Reference Image
        img_bytes = create_test_image_bytes()
        ref_res = await client.post(
            f"/api/v1/investigations/{inv_id}/reference-image",
            files={"file": ("reference_photo.jpg", img_bytes, "image/jpeg")},
            data={"label": "Official Target Portrait"},
            headers=auth_headers,
        )
        assert ref_res.status_code == 201, ref_res.text

        # Mock normalized discoveries returned by SearchAPIGoogleLensProvider
        mock_discoveries = [
            NormalizedDiscoveryResult(
                provider="SearchAPIGoogleLens",
                source_url="https://press.example.org/news/executive.jpg",
                page_url="https://press.example.org/news/executive.jpg",
                image_url="https://press.example.org/news/executive.jpg",
                domain="press.example.org",
                page_title="Executive Press Release Photo",
                discovered_at=datetime.now(timezone.utc),
                provider_score=1.0,
                provider_raw_ref="exact_matches",
                c2pa_status=None,
                metadata={
                    "match_type": "EXACT",
                    "snippet": "Official press photo release.",
                    "search_id": "lens_test_001",
                },
            ),
            NormalizedDiscoveryResult(
                provider="SearchAPIGoogleLens",
                source_url="https://social.example.org/profile/asset",
                page_url="https://social.example.org/profile/asset",
                image_url="https://social.example.org/img/avatar.png",
                domain="social.example.org",
                page_title="Social Media Profile Match",
                discovered_at=datetime.now(timezone.utc),
                provider_score=0.85,
                provider_raw_ref="visual_matches",
                c2pa_status=None,
                metadata={
                    "match_type": "VISUALLY_SIMILAR",
                    "snippet": "User profile avatar match.",
                    "search_id": "lens_test_001",
                },
            ),
        ]

        # 4. Call POST /api/v1/investigations/{id}/web-search
        with patch.object(
            provider_orchestrator.searchapi_provider,
            "discover",
            return_value=mock_discoveries,
        ):
            search_res = await client.post(
                f"/api/v1/investigations/{inv_id}/web-search",
                json={"max_results": 20, "include_similar": True},
                headers=auth_headers,
            )
            assert search_res.status_code == 200, search_res.text
            data = search_res.json()
            assert data["provider"] == "SearchAPIGoogleLens"
            assert data["results_count"] == 2
            assert len(data["candidates"]) == 2
            assert data["status"] == "COMPLETED"

            # Check candidate details
            c1 = data["candidates"][0]
            assert c1["domain"] == "press.example.org"
            assert c1["metadata"]["verification_status"] == "PENDING_REVIEW"
            assert c1["metadata"]["match_type"] == "EXACT"

        # 5. Fetch Findings endpoint
        findings_res = await client.get(
            f"/api/v1/investigations/{inv_id}/findings",
            headers=auth_headers,
        )
        assert findings_res.status_code == 200, findings_res.text
        findings_data = findings_res.json()
        assert findings_data["total_findings"] == 2
        assert findings_data["findings"][0]["provider"] == "SearchAPIGoogleLens"

    async def test_searchapi_web_search_missing_image_fails(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        case_res = await client.post(
            "/api/v1/investigations",
            json={"title": "Empty Lens Case", "description": "No image yet"},
            headers=auth_headers,
        )
        assert case_res.status_code == 201
        inv_id = case_res.json()["id"]

        res = await client.post(
            f"/api/v1/investigations/{inv_id}/web-search",
            json={"max_results": 10},
            headers=auth_headers,
        )
        assert res.status_code == 400
        assert "no reference image" in res.json()["detail"].lower()
