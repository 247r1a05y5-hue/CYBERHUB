"""Integration test for POST /api/v1/investigations/{id}/web-search endpoint."""
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
    img = Image.new("RGB", (128, 128), color=(45, 90, 135))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
class TestGoogleWebSearchAPI:
    """Tests for the real Google Cloud Vision Web Detection endpoint."""

    async def test_web_search_full_lifecycle(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        # 1. Create Investigation
        case_res = await client.post(
            "/api/v1/investigations",
            json={"title": "Web Search Test Case", "description": "Testing Vision API integration"},
            headers=auth_headers,
        )
        assert case_res.status_code == 201, case_res.text
        inv_id = case_res.json()["id"]

        # 2. Attest Case
        att_res = await client.post(
            f"/api/v1/investigations/{inv_id}/attestation",
            json={
                "purpose": "AUTHORIZED_SECURITY_AUDIT",
                "authority_basis": "Incident Response Retainer #CYBER-99",
                "attestation_text": "I hereby certify under penalty of perjury that this investigation is fully authorized.",
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
            files={"file": ("reference.jpg", img_bytes, "image/jpeg")},
            data={"label": "Official ID Headshot"},
            headers=auth_headers,
        )
        assert ref_res.status_code == 201, ref_res.text

        # Mock normalized discoveries from Google Cloud Vision
        mock_discoveries = [
            NormalizedDiscoveryResult(
                provider="GoogleCloudVision",
                source_url="https://press.example.org/news/portrait.jpg",
                page_url="https://press.example.org/news/portrait.jpg",
                image_url="https://press.example.org/news/portrait.jpg",
                domain="press.example.org",
                page_title="Official Press Release Headshot",
                discovered_at=datetime.now(timezone.utc),
                provider_score=1.0,
                provider_raw_ref="full_matching_images",
                c2pa_status=None,
                metadata={
                    "match_type": "FULL_MATCH",
                    "best_guess_labels": ["Executive Portrait"],
                    "web_entities": [{"entity_id": "/m/01", "description": "Security", "score": 0.95}],
                },
            ),
            NormalizedDiscoveryResult(
                provider="GoogleCloudVision",
                source_url="https://social.example.org/profile/4412",
                page_url="https://social.example.org/profile/4412",
                image_url="https://social.example.org/media/crop_4412.jpg",
                domain="social.example.org",
                page_title="Public Social Account",
                discovered_at=datetime.now(timezone.utc),
                provider_score=0.85,
                provider_raw_ref="pages_with_matching_images",
                c2pa_status=None,
                metadata={
                    "match_type": "PAGE_MATCH",
                    "best_guess_labels": ["Executive Portrait"],
                },
            ),
        ]

        # 4. Call POST /api/v1/investigations/{id}/web-search
        with patch.object(
            provider_orchestrator.google_provider,
            "discover",
            return_value=mock_discoveries,
        ):
            search_res = await client.post(
                f"/api/v1/investigations/{inv_id}/web-search",
                json={"max_results": 25, "include_similar": True},
                headers=auth_headers,
            )
            assert search_res.status_code == 200, search_res.text
            data = search_res.json()
            assert data["provider"] == "GoogleCloudVision"
            assert data["results_count"] == 2
            assert len(data["candidates"]) == 2
            assert data["best_guess_labels"] == ["Executive Portrait"]
            assert data["status"] == "COMPLETED"

            # Check candidate properties
            c1 = data["candidates"][0]
            assert c1["domain"] == "press.example.org"
            assert c1["metadata"]["verification_status"] == "PENDING_REVIEW"
            assert c1["source_url"] == "https://press.example.org/news/portrait.jpg"

        # 5. Verify Findings Endpoint returns the new candidates
        findings_res = await client.get(
            f"/api/v1/investigations/{inv_id}/findings",
            headers=auth_headers,
        )
        assert findings_res.status_code == 200, findings_res.text
        findings_data = findings_res.json()
        assert findings_data["total_findings"] == 2
        assert findings_data["findings"][0]["provider"] == "GoogleCloudVision"

    async def test_web_search_without_reference_image_fails(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Web search must fail with 400 if no reference image has been captured/uploaded."""
        case_res = await client.post(
            "/api/v1/investigations",
            json={"title": "Empty Case", "description": "No image uploaded yet"},
            headers=auth_headers,
        )
        assert case_res.status_code == 201
        inv_id = case_res.json()["id"]

        res = await client.post(
            f"/api/v1/investigations/{inv_id}/web-search",
            json={"max_results": 10},
            headers=auth_headers,
        )
        assert res.status_code == 400, res.text
        assert "no reference image" in res.json()["detail"].lower()

    async def test_web_search_tenant_isolation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Web search cannot be triggered on cases belonging to other tenants."""
        foreign_id = str(uuid.uuid4())
        res = await client.post(
            f"/api/v1/investigations/{foreign_id}/web-search",
            json={"max_results": 10},
            headers=auth_headers,
        )
        assert res.status_code in (403, 404), res.text
