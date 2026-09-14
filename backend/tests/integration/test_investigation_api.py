"""Integration tests for Image Exposure Investigation Endpoints.

Tests full REST workflow:
1. POST /api/v1/investigations (Create Investigation Container)
2. POST /api/v1/investigations/{id}/attestation (Authorization Attestation)
3. POST /api/v1/investigations/{id}/reference-image (Upload Image & Compute DINOv2 / Hashes)
4. POST /api/v1/investigations/{id}/scan (Trigger Exposure Scan via Mock Provider)
5. GET  /api/v1/investigations/{id}/findings (List Findings & Clusters)
6. POST /api/v1/investigations/{id}/findings/{fid}/verify (Human Review Gate)
7. POST /api/v1/investigations/{id}/risk (Evaluate Risk Level)
8. POST /api/v1/investigations/{id}/report (Generate Hash-Referenced Forensic Report)
"""
from __future__ import annotations

import io
import pytest
from httpx import AsyncClient
from PIL import Image

from tests.fixtures.synthetic_corpus import create_base_synthetic_image, get_image_bytes


@pytest.mark.asyncio
class TestInvestigationWorkflowAPI:
    async def test_full_investigation_lifecycle(self, client: AsyncClient, auth_headers: dict[str, str]):
        # 1. Create Investigation
        res = await client.post(
            "/api/v1/investigations",
            json={"title": "Executive Image Exposure Audit", "description": "Investigating unauthorized appearance"},
            headers=auth_headers,
        )
        assert res.status_code == 201, res.text
        inv_data = res.json()
        inv_id = inv_data["id"]
        assert inv_id is not None
        assert inv_data["title"] == "Executive Image Exposure Audit"

        # 2. Submit Authorization Attestation
        # Generate image first to get its hash
        base_img = create_base_synthetic_image()
        img_bytes = get_image_bytes(base_img, format="PNG")
        
        att_res = await client.post(
            f"/api/v1/investigations/{inv_id}/attestation",
            json={
                "attestation_text": "I certify under penalty of policy that I have full authorization to investigate this image.",
                "policy_version": "v1.0",
                "reference_image_sha256": "placeholder_or_real",
            },
            headers=auth_headers,
        )
        assert att_res.status_code == 201, att_res.text
        att_data = att_res.json()
        assert att_data["is_policy_record"] is True

        # 3. Upload Reference Image
        upload_files = {"file": ("reference_photo.png", img_bytes, "image/png")}
        upload_res = await client.post(
            f"/api/v1/investigations/{inv_id}/reference-image",
            files=upload_files,
            headers=auth_headers,
        )
        assert upload_res.status_code == 201, upload_res.text
        ref_data = upload_res.json()
        assert ref_data["sha256"] is not None
        assert ref_data["phash"] is not None
        assert ref_data["dhash"] is not None
        assert ref_data["dinov2_indexed"] is True

        # 4. Trigger Scan with Mock Provider
        scan_res = await client.post(
            f"/api/v1/investigations/{inv_id}/scan",
            json={"providers": ["deterministic_mock"]},
            headers=auth_headers,
        )
        assert scan_res.status_code == 202, scan_res.text
        scan_data = scan_res.json()
        assert scan_data["status"] in ("QUEUED", "RUNNING", "COMPLETED", "READY_FOR_REVIEW")

        # 5. Fetch Findings & Clusters
        findings_res = await client.get(
            f"/api/v1/investigations/{inv_id}/findings",
            headers=auth_headers,
        )
        assert findings_res.status_code == 200, findings_res.text
        findings_data = findings_res.json()
        assert "findings" in findings_data
        assert "clusters" in findings_data
        findings = findings_data["findings"]
        assert len(findings) > 0

        first_finding_id = findings[0]["id"]

        # 6. Human-in-the-Loop Review Gate (Verify Finding)
        verify_res = await client.post(
            f"/api/v1/investigations/{inv_id}/findings/{first_finding_id}/verify",
            json={"status": "VERIFIED", "review_notes": "Confirmed match on external blog."},
            headers=auth_headers,
        )
        assert verify_res.status_code == 200, verify_res.text
        assert verify_res.json()["verification_status"] == "VERIFIED"

        # 7. Evaluate Deterministic Risk
        risk_res = await client.post(
            f"/api/v1/investigations/{inv_id}/risk",
            headers=auth_headers,
        )
        assert risk_res.status_code == 200, risk_res.text
        risk_data = risk_res.json()
        assert risk_data["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert "contributing_factors" in risk_data

        # 8. Generate Forensic Report (JSON format)
        report_res = await client.post(
            f"/api/v1/investigations/{inv_id}/report",
            json={"format": "JSON", "include_audit_trail": True},
            headers=auth_headers,
        )
        assert report_res.status_code == 200, report_res.text
        report_data = report_res.json()
        assert report_data["investigation_id"] == inv_id
        assert report_data["reference_image_sha256"] is not None
        assert report_data["methodology"] is not None

        # 9. Generate Response / Takedown Package
        resp_pkg_res = await client.post(
            f"/api/v1/investigations/{inv_id}/response-packages",
            json={
                "target_domain": "social.example.test",
                "target_entity": "Hostmaster Support",
                "format": "MARKDOWN",
            },
            headers=auth_headers,
        )
        assert resp_pkg_res.status_code == 201, resp_pkg_res.text
        pkg_data = resp_pkg_res.json()
        assert pkg_data["package_number"] is not None
        assert "takedown_letter" in pkg_data

        # 10. Configure Continuous Monitoring
        mon_cfg_res = await client.post(
            f"/api/v1/investigations/{inv_id}/monitoring",
            json={"frequency": "DAILY", "enabled": True},
            headers=auth_headers,
        )
        assert mon_cfg_res.status_code == 200, mon_cfg_res.text
        mon_cfg = mon_cfg_res.json()
        assert mon_cfg["enabled"] is True
        assert mon_cfg["frequency"] == "DAILY"

        # 11. Retrieve Monitoring Status
        mon_status_res = await client.get(
            f"/api/v1/investigations/{inv_id}/monitoring",
            headers=auth_headers,
        )
        assert mon_status_res.status_code == 200, mon_status_res.text
        assert mon_status_res.json()["is_configured"] is True

        # 12. Trigger Monitoring Re-Scan
        mon_scan_res = await client.post(
            f"/api/v1/investigations/{inv_id}/monitoring/scan",
            headers=auth_headers,
        )
        assert mon_scan_res.status_code == 200, mon_scan_res.text
        assert mon_scan_res.json()["status"] == "COMPLETED"

        # 13. Cross-Store Retention Purge
        del_res = await client.delete(
            f"/api/v1/investigations/{inv_id}",
            headers=auth_headers,
        )
        assert del_res.status_code == 200, del_res.text
        assert del_res.json()["status"] in ("PURGED", "PURGED_SUCCESSFULLY")
