"""Unit tests for Incident FSM and Activity Notes."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_incident_lifecycle_fsm(client: AsyncClient, auth_headers: dict[str, str]):
    # 1. Create incident
    create_payload = {
        "title": "Unauthorized Access Anomaly",
        "description": "Suspicious login attempts from multiple geolocations",
        "severity": "high",
        "status": "new",
    }
    resp = await client.post("/api/v1/incidents", json=create_payload, headers=auth_headers)
    assert resp.status_code == 201
    inc = resp.json()
    inc_id = inc["id"]
    assert inc["status"] == "new"

    # 2. Transition new -> triaged (valid)
    t1 = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"status": "triaged", "note": "Triaged by security analyst"},
        headers=auth_headers,
    )
    assert t1.status_code == 200
    assert t1.json()["status"] == "triaged"

    # 3. Invalid transition triaged -> resolved directly (should fail 422)
    invalid_t = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"status": "resolved", "note": "Trying to skip investigation"},
        headers=auth_headers,
    )
    assert invalid_t.status_code == 422

    # 4. Transition triaged -> investigating
    t2 = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"status": "investigating", "note": "Starting endpoint memory dump"},
        headers=auth_headers,
    )
    assert t2.status_code == 200
    assert t2.json()["status"] == "investigating"

    # 5. Add note
    note_resp = await client.post(
        f"/api/v1/incidents/{inc_id}/notes",
        json={"content": "Verified attacker IP blocked at router"},
        headers=auth_headers,
    )
    assert note_resp.status_code == 201

    # 6. Transition to resolved with note
    t3 = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"status": "resolved", "note": "Containment verified and confirmed clean."},
        headers=auth_headers,
    )
    assert t3.status_code == 200
    assert t3.json()["status"] == "resolved"
