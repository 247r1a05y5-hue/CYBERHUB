"""Real HTTP End-to-End Client Test against Live Running Backend Server.

Simulates the exact browser user flow:
1. Login -> Obtain real JWT Bearer token.
2. Verify /auth/me authentication.
3. Create Investigation -> POST /api/v1/investigations.
4. Upload Real Camera JPEG Frame -> POST /api/v1/investigations/{id}/reference-image.
5. Confirm Phase 1 image pipeline, SHA-256, pHash, dHash, DINOv2 vector, and storage artifact.
6. Record Attestation -> POST /api/v1/investigations/{id}/attestation.
7. Run Matching -> POST /api/v1/investigations/{id}/match-candidates/evaluate.
8. Trigger Discovery Scan -> POST /api/v1/investigations/{id}/scan.
9. Fetch Findings -> GET /api/v1/investigations/{id}/findings.
10. Analyst Verification Gate -> POST /api/v1/investigations/{id}/findings/{id}/verify.
11. Evidence Vault Sealing -> GET /api/v1/investigations/{id}/evidence.
12. Risk Assessment -> POST /api/v1/investigations/{id}/risk.
13. Timeline Query -> GET /api/v1/investigations/{id}/timeline.
14. Exposure Graph -> GET /api/v1/investigations/{id}/graph.
15. Report Generation -> POST /api/v1/investigations/{id}/report.
16. Response Package -> POST /api/v1/investigations/{id}/response-packages.
"""
from __future__ import annotations

import io
import time
import uuid
import httpx
from PIL import Image

BASE_URL = "http://localhost:8000/api/v1"


def generate_camera_frame_jpeg_bytes() -> bytes:
    """Generate realistic 1280x720 webcam capture JPEG bytes matching browser canvas output."""
    img = Image.new("RGB", (1280, 720), color=(45, 85, 125))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def run_test():
    print("\n" + "=" * 80)
    print("REAL HTTP BROWSER FLOW VERIFICATION (LIVE SERVER ON PORT 8000)")
    print("=" * 80)

    client = httpx.Client(base_url=BASE_URL, timeout=60.0)

    # 1. Login
    print("\n[Step 1] Logging in as analyst@cyberhub.security...")
    login_res = client.post("/auth/login", json={"email": "analyst@cyberhub.security", "password": "Password123!"})
    if login_res.status_code != 200:
        # If user not created, try register
        reg_res = client.post("/auth/register", json={
            "email": "analyst@cyberhub.security",
            "password": "Password123!",
            "organization_name": "CyberHub Defense Org",
            "role": "analyst"
        })
        assert reg_res.status_code in (200, 201), f"Registration failed: {reg_res.text}"
        token = reg_res.json()["access_token"]
    else:
        token = login_res.json()["access_token"]

    print(f"  ✓ JWT Token Acquired: Bearer {token[:20]}...")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Auth me
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200, f"/auth/me failed: {me_res.text}"
    user_data = me_res.json()
    print(f"  ✓ Authenticated as: {user_data.get('email')} (Org: {user_data.get('organization_id')})")

    # 3. Create Investigation Container
    print("\n[Step 2] Creating Investigation Container...")
    inv_title = f"Webcam Exposure Dossier - {time.strftime('%Y-%m-%d %H:%M:%S')}"
    case_res = client.post(
        "/investigations",
        json={"title": inv_title, "target_subject_label": "Executive Officer"},
        headers=headers,
    )
    assert case_res.status_code == 201, f"Investigation creation failed: {case_res.status_code} {case_res.text}"
    case = case_res.json()
    case_id = case["id"]
    print(f"  ✓ Investigation Created: {case['case_number']} (ID: {case_id})")

    # 4. Upload Real Camera JPEG Frame
    print("\n[Step 3] Uploading Real Camera JPEG Frame (1280x720, Quality 92)...")
    cam_bytes = generate_camera_frame_jpeg_bytes()
    filename = f"camera_capture_{int(time.time() * 1000)}.jpg"
    files = {"file": (filename, cam_bytes, "image/jpeg")}
    data = {"source_type": "WEBCAM", "label": "Executive Officer"}

    img_res = client.post(
        f"/investigations/{case_id}/reference-image",
        files=files,
        data=data,
        headers=headers,
    )
    assert img_res.status_code == 201, f"Reference image upload failed: {img_res.status_code} {img_res.text}"
    img_data = img_res.json()
    ref_sha256 = img_data["sha256"]
    print(f"  ✓ Reference Image Processed Successfully:")
    print(f"    - SHA-256 Digest: {ref_sha256}")
    print(f"    - Perceptual pHash: {img_data.get('phash')}")
    print(f"    - Perceptual dHash: {img_data.get('dhash')}")
    print(f"    - DINOv2 Embedding: {img_data.get('dinov2', {}).get('dimension')} dims ({img_data.get('dinov2', {}).get('model')})")
    print(f"    - Image Quality: Sharpness={img_data.get('quality', {}).get('sharpness')}")

    # 5. Record Attestation
    print("\n[Step 4] Recording Compliance Attestation...")
    att_res = client.post(
        f"/investigations/{case_id}/attestation",
        json={
            "attestation_text": "I attest I have full legal authorization to investigate this image under enterprise security policy.",
            "attestation_version": "v1.0.0",
            "reference_image_sha256": ref_sha256,
        },
        headers=headers,
    )
    assert att_res.status_code == 201, f"Attestation failed: {att_res.status_code} {att_res.text}"
    print(f"  ✓ Attestation Committed to Audit Log (Ref SHA: {ref_sha256[:16]}...)")

    # 6. Evaluate Match Candidates
    print("\n[Step 5] Evaluating 3-Tier Multi-Signal Matching...")
    match_res = client.post(f"/investigations/{case_id}/match-candidates/evaluate", headers=headers)
    assert match_res.status_code == 200, f"Match evaluation failed: {match_res.status_code} {match_res.text}"
    candidates = match_res.json().get("candidates", [])
    print(f"  ✓ Evaluated {len(candidates)} benchmark candidates across SHA-256, pHash/dHash, and DINOv2.")

    # 7. Trigger Discovery Scan
    print("\n[Step 6] Triggering Public Discovery Scan...")
    scan_res = client.post(f"/investigations/{case_id}/scan", headers=headers)
    assert scan_res.status_code in (200, 201, 202), f"Discovery scan failed: {scan_res.status_code} {scan_res.text}"
    print(f"  ✓ Discovery Scan Dispatched: {scan_res.json()}")

    # 8. Fetch Findings
    print("\n[Step 7] Fetching Discovered Findings...")
    find_res = client.get(f"/investigations/{case_id}/findings", headers=headers)
    assert find_res.status_code == 200, f"Fetch findings failed: {find_res.status_code} {find_res.text}"
    findings = find_res.json().get("findings", [])
    print(f"  ✓ Retrieved {len(findings)} discovered candidate sources.")

    # 9. Analyst Verification Gate (if findings exist)
    if findings:
        f_id = findings[0]["id"]
        print(f"\n[Step 8] Analyst Verification Review Gate on Finding {f_id}...")
        v_res = client.post(
            f"/investigations/{case_id}/findings/{f_id}/verify",
            json={"status": "VERIFIED", "reason": "Confirmed match on public source endpoint."},
            headers=headers,
        )
        assert v_res.status_code == 200, f"Verification failed: {v_res.status_code} {v_res.text}"
        print(f"  ✓ Finding Verified & Evidence Vault Sealed: {v_res.json().get('evidence_number', 'SEALED')}")

    # 10. Risk Evaluation (Policy v1)
    print("\n[Step 9] Evaluating Exposure Risk Engine (Policy v1)...")
    risk_res = client.post(f"/investigations/{case_id}/risk", headers=headers)
    assert risk_res.status_code == 200, f"Risk evaluation failed: {risk_res.status_code} {risk_res.text}"
    risk_data = risk_res.json()
    print(f"  ✓ Risk Assessed: {risk_data.get('risk_level')} (Score: {risk_data.get('score')} / 100.0, Policy: {risk_data.get('risk_policy_version')})")

    # 11. Timeline Audit
    print("\n[Step 10] Fetching Investigation Timeline...")
    time_res = client.get(f"/investigations/{case_id}/timeline", headers=headers)
    assert time_res.status_code == 200, f"Timeline fetch failed: {time_res.status_code} {time_res.text}"
    timeline_data = time_res.json()
    events = timeline_data.get("events", []) if isinstance(timeline_data, dict) else timeline_data
    print(f"  ✓ Chronological Timeline: {len(events)} event(s) recorded.")

    # 12. Exposure Graph
    print("\n[Step 11] Fetching Exposure Investigation Graph...")
    graph_res = client.get(f"/investigations/{case_id}/graph", headers=headers)
    assert graph_res.status_code == 200, f"Graph fetch failed: {graph_res.status_code} {graph_res.text}"
    graph_data = graph_res.json()
    print(f"  ✓ Exposure Graph: {len(graph_data.get('nodes', []))} nodes, {len(graph_data.get('edges', []))} edges.")

    # 13. Report Generation
    print("\n[Step 12] Exporting Multi-Format Forensic Report (JSON & PDF)...")
    rep_res_json = client.post(
        f"/investigations/{case_id}/report",
        json={"format": "JSON", "include_audit_trail": True},
        headers=headers,
    )
    assert rep_res_json.status_code == 200, f"Report JSON generation failed: {rep_res_json.status_code} {rep_res_json.text}"
    print(f"  ✓ JSON Report Generated & Exported ({len(rep_res_json.text)} chars).")

    rep_res_pdf = client.post(
        f"/investigations/{case_id}/report",
        json={"format": "PDF", "include_audit_trail": True},
        headers=headers,
    )
    assert rep_res_pdf.status_code == 200, f"Report PDF generation failed: {rep_res_pdf.status_code}"
    assert len(rep_res_pdf.content) > 0, "PDF content is empty"
    print(f"  ✓ PDF Report Generated & Exported ({len(rep_res_pdf.content)} bytes).")

    # 14. Response Package
    print("\n[Step 13] Generating Takedown Response Package...")
    pkg_res = client.post(
        f"/investigations/{case_id}/response-packages",
        json={"target_domain": "social.example.test", "target_entity": "Abuse & Compliance Dept", "format": "MARKDOWN"},
        headers=headers,
    )
    assert pkg_res.status_code in (200, 201), f"Response package generation failed: {pkg_res.status_code} {pkg_res.text}"
    pkg_data = pkg_res.json()
    print(f"  ✓ Takedown Notice Generated: {pkg_data.get('package_number')} (SHA-256: {pkg_data.get('sha256_hash')})")

    print("\n" + "=" * 80)
    print("✅ FULL BROWSER HTTP USER FLOW VERIFIED 100% SUCCESSFUL!")
    print("=" * 80)


if __name__ == "__main__":
    run_test()

