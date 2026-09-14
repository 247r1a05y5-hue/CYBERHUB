"""Alerts unit tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_alert_creation_and_deduplication(client: AsyncClient, auth_headers: dict[str, str]):
    alert_payload = {
        "title": "Port Scanning Activity Detected",
        "description": "Repeated connection attempts across multiple ports",
        "severity": "medium",
        "status": "open",
        "dedup_key": "custom-dedup-key-001",
    }
    # 1. First creation
    r1 = await client.post("/api/v1/alerts", json=alert_payload, headers=auth_headers)
    assert r1.status_code in (200, 201)
    alert1 = r1.json()

    # 2. Second creation with same dedup_key -> returns existing alert (idempotent)
    r2 = await client.post("/api/v1/alerts", json=alert_payload, headers=auth_headers)
    assert r2.status_code in (200, 201)
    alert2 = r2.json()
    assert alert1["id"] == alert2["id"]

    # 3. Update alert status
    update_payload = {"status": "acknowledged"}
    r3 = await client.patch(f"/api/v1/alerts/{alert1['id']}", json=update_payload, headers=auth_headers)
    assert r3.status_code == 200
    assert r3.json()["status"] == "acknowledged"
