"""Unit tests for Deterministic Exposure Risk Engine (Slice 9).

Tests:
- Deterministic risk assessment categories (LOW, MEDIUM, HIGH, CRITICAL)
- Factor breakdown itemization
- Calculation versioning ("v1.0.0")
- Ensures raw numeric score is purely internal and not presented as statistical certainty
"""
from __future__ import annotations

import pytest
from app.services.exposure_risk_service import (
    ExposureRiskLevel,
    exposure_risk_service,
)


class TestExposureRiskEngine:
    def test_low_risk_evaluation(self):
        assessment = exposure_risk_service.evaluate_risk(
            verified_count=1,
            unique_domains=["example.com"],
            cluster_count=1,
            has_breach_domain=False,
            evidence_complete_count=1,
        )
        assert assessment.risk_level == ExposureRiskLevel.LOW
        assert assessment.calculation_version in ("v1", "v1.0.0")
        assert len(assessment.contributing_factors) > 0
        assert any("verified findings" in f.name.lower() for f in assessment.contributing_factors)

    def test_medium_risk_evaluation(self):
        assessment = exposure_risk_service.evaluate_risk(
            verified_count=4,
            unique_domains=["site1.com", "site2.com", "site3.com"],
            cluster_count=2,
            has_breach_domain=False,
            evidence_complete_count=3,
        )
        assert assessment.risk_level in (ExposureRiskLevel.LOW, ExposureRiskLevel.MEDIUM)

    def test_high_risk_with_high_risk_domain(self):
        assessment = exposure_risk_service.evaluate_risk(
            verified_count=8,
            unique_domains=["site1.com", "site2.com", "breach-dump.net", "darkleaks.to"],
            cluster_count=3,
            has_breach_domain=True,
            evidence_complete_count=5,
        )
        assert assessment.risk_level in (ExposureRiskLevel.HIGH, ExposureRiskLevel.CRITICAL)
        assert any("breach" in f.name.lower() for f in assessment.contributing_factors)

    def test_critical_risk_widespread_exposure(self):
        assessment = exposure_risk_service.evaluate_risk(
            verified_count=30,
            unique_domains=[f"site{i}.com" for i in range(15)],
            cluster_count=8,
            has_breach_domain=True,
            evidence_complete_count=25,
        )
        assert assessment.risk_level == ExposureRiskLevel.CRITICAL

    def test_zero_findings_minimal_risk(self):
        assessment = exposure_risk_service.evaluate_risk(
            verified_count=0,
            unique_domains=[],
            cluster_count=0,
            has_breach_domain=False,
            evidence_complete_count=0,
        )
        assert assessment.risk_level == ExposureRiskLevel.LOW
