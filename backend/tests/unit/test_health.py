"""Health check tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "cyber-platform-api"


@pytest.mark.asyncio
async def test_ready_endpoint(client: AsyncClient):
    from unittest.mock import patch, AsyncMock, MagicMock
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_ctx.__aexit__.return_value = None

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_ctx

    with patch("app.api.v1.endpoints.health.engine", mock_engine):
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
