"""Unit and integration tests for analysis submission and execution."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_submit_and_retrieve_analysis(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {
        "analyzer_type": "mock",
        "input_type": "text",
        "payload": "powershell -enc JABzACAAPQAg... cmd.exe 198.51.100.1",
        "raw_metadata": {"source": "EDR Sensor"},
    }
    resp = await client.post("/api/v1/analyses", json=payload, headers=auth_headers)
    assert resp.status_code in (200, 201, 202)
    analysis = resp.json()
    analysis_id = analysis["id"]
    assert analysis["status"] in ("completed", "running", "queued")

    # Fetch details
    detail_resp = await client.get(f"/api/v1/analyses/{analysis_id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == analysis_id
    assert detail["input"] is not None


@pytest.mark.asyncio
async def test_list_analyses_with_pagination(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.get("/api/v1/analyses?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
