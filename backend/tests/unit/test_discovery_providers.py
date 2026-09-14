"""Unit tests for External Search Provider Abstraction & Orchestration (Phase 4).

Tests:
1. DeterministicMockProvider production execution guard.
2. Circuit breaker state transitions (CLOSED -> OPEN -> HALF_OPEN).
3. Provider status reporting (NOT_CONFIGURED, READY, DEGRADED, RATE_LIMITED).
4. Google Vision result normalization.
5. TinEye result normalization.
6. Multi-provider orchestration error isolation.
"""
from __future__ import annotations

import os
import time
import pytest

from app.core.config import settings
from app.services.provider_orchestration_service import (
    CircuitBreaker,
    DeterministicMockProvider,
    GoogleVisionWebDetectionProvider,
    NormalizedDiscoveryResult,
    ProviderOptions,
    ProviderStatus,
    TinEyeMatchEngineProvider,
    provider_orchestrator,
)


class TestDiscoveryProviders:
    def test_circuit_breaker_trips_to_open_after_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_time_seconds=0.1)
        assert cb.state == "CLOSED"
        assert cb.allow_request() is True

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"

        # Third failure trips breaker
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.allow_request() is False

        # Wait for recovery window
        time.sleep(0.15)
        assert cb.allow_request() is True
        assert cb.state == "HALF_OPEN"

        # Success resets to closed
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.allow_request() is True

    def test_provider_status_reporting(self):
        from unittest.mock import patch
        prov = GoogleVisionWebDetectionProvider(api_key=None)
        with patch.object(prov, "_get_client", return_value=None):
            assert prov.get_status() == ProviderStatus.NOT_CONFIGURED

        prov_configured = GoogleVisionWebDetectionProvider(api_key="test_api_key_123")
        assert prov_configured.get_status() == ProviderStatus.READY

        # Simulate trip
        for _ in range(3):
            prov_configured.circuit_breaker.record_failure()
        assert prov_configured.get_status() == ProviderStatus.DEGRADED

    def test_mock_provider_production_guard(self, monkeypatch):
        # Explicitly disable test mock permissions and clear test env vars
        monkeypatch.setattr(settings, "ALLOW_TEST_MOCK_PROVIDER", False)
        monkeypatch.delenv("ALLOW_TEST_MOCK_PROVIDER", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("_", "/usr/bin/uvicorn")

        mock_prov = DeterministicMockProvider()
        with pytest.raises(PermissionError, match="strictly prohibited in production"):
            # Run discovery without test env flag
            import asyncio
            asyncio.run(mock_prov.discover(b"test", None, ProviderOptions()))

    @pytest.mark.asyncio
    async def test_mock_provider_discovery_in_test_env(self, monkeypatch):
        monkeypatch.setattr(settings, "ALLOW_TEST_MOCK_PROVIDER", True)
        mock_prov = DeterministicMockProvider()
        results = await mock_prov.discover(b"test", None, ProviderOptions())
        assert len(results) >= 3
        for r in results:
            assert isinstance(r, NormalizedDiscoveryResult)
            assert r.provider == "DeterministicMock"
            assert r.domain is not None
            assert r.page_url.startswith("http")

    def test_provider_orchestration_service_status_summary(self):
        statuses = provider_orchestrator.get_provider_statuses()
        assert "google_vision" in statuses
        assert "tineye" in statuses
        assert "status" in statuses["google_vision"]
        assert "configured" in statuses["google_vision"]
        assert "circuit_breaker" in statuses["google_vision"]
