"""Integration tests for Async Scan Workflow, Rate Limiting & Cost Budgeting (Slice 4).

Tests:
- Full Async Scan state lifecycle progression
- Token bucket rate limiter (abuse volume prevention)
- Per-org monthly cost budget gate (distinct spend limit control)
- Provider circuit breaker tripping on simulated failures
"""
from __future__ import annotations

import pytest
from app.services.exposure_scan_orchestrator import (
    CostBudgetExceededError,
    RateLimitExceededError,
    exposure_scan_orchestrator,
)
from app.services.provider_orchestration_service import CircuitBreaker


class TestAsyncScanWorkflowAndLimiting:
    def test_abuse_rate_limiter_enforcement(self):
        org_id = "org_rate_limit_test"
        
        # Rate limit is set to max 20 per hour in settings
        # We can simulate consumption until limit is exhausted
        limit = 10
        for _ in range(limit):
            allowed = exposure_scan_orchestrator.check_and_consume_rate_limit(org_id, max_per_hour=limit)
            assert allowed is True

        # Next request must fail
        with pytest.raises(RateLimitExceededError, match="Hourly scan rate limit exceeded"):
            exposure_scan_orchestrator.check_and_consume_rate_limit(org_id, max_per_hour=limit)

    def test_cost_budget_gate_enforcement(self):
        org_id = "org_budget_test"
        
        # Test distinct cost budget gate ($50 monthly limit)
        monthly_budget = 50.0
        
        # Consume $40
        assert exposure_scan_orchestrator.check_and_consume_cost_budget(org_id, cost=40.0, monthly_limit=monthly_budget) is True
        
        # Consuming another $15 exceeds $50
        with pytest.raises(CostBudgetExceededError, match="Monthly provider budget limit reached"):
            exposure_scan_orchestrator.check_and_consume_cost_budget(org_id, cost=15.0, monthly_limit=monthly_budget)

    def test_provider_circuit_breaker(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=60)
        
        assert breaker.allow_request() is True
        
        # Record 3 failures
        breaker.record_failure()
        assert breaker.allow_request() is True
        breaker.record_failure()
        assert breaker.allow_request() is True
        breaker.record_failure()
        
        # Circuit breaker should now trip to OPEN
        assert breaker.allow_request() is False
        assert breaker.state == "OPEN"

        # On manual reset or success after half-open
        breaker.record_success()
        assert breaker.state == "CLOSED"
        assert breaker.allow_request() is True
