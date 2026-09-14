"""Deterministic Exposure Risk Assessment Engine.

Specifications:
- Output Categories: LOW, MEDIUM, HIGH, CRITICAL
- Risk Policy Version: v1 (strictly enforced)
- Gating: Strictly evaluated on human-verified exposures (VERIFIED status).
- 0-Finding State: Explicitly deterministic LOW tier with 0 score, 0 verified count, and informative explanation.
- Factors:
  1. Verified Findings Volume (weight: 35%)
  2. Domain Spread & Proliferation (weight: 25%)
  3. Breach & High-Risk Repositories (weight: 30%)
  4. Forensic Completeness & Clustering (weight: 10%)
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

RISK_POLICY_VERSION = "v1"


class ExposureRiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class RiskFactorDetail:
    """Individual factor contributing to exposure risk tier."""
    name: str
    weight: float
    contribution: float
    detail: str


@dataclass(frozen=True)
class ExposureRiskEvaluation:
    """Deterministic risk output."""
    risk_level: ExposureRiskLevel
    internal_score: float  # 0.0 to 100.0
    risk_policy_version: str
    contributing_factors: list[RiskFactorDetail]
    explanation: str
    verified_count: int
    unique_domains: int

    @property
    def calculation_version(self) -> str:
        return self.risk_policy_version


class ExposureRiskService:
    """Computes deterministic exposure risk assessments."""

    def evaluate_risk(
        self,
        verified_count: int,
        unique_domains: list[str],
        cluster_count: int,
        has_breach_domain: bool,
        evidence_complete_count: int,
    ) -> ExposureRiskEvaluation:
        """Run deterministic multi-factor weighted risk evaluation under policy v1."""
        factors: list[RiskFactorDetail] = []
        domain_count = len(unique_domains)

        # Handle explicit 0-finding state
        if verified_count == 0:
            factors = [
                RiskFactorDetail(
                    name="Verified Findings Volume",
                    weight=0.35,
                    contribution=0.0,
                    detail="0 verified exposure endpoints confirmed.",
                ),
                RiskFactorDetail(
                    name="Domain Spread & Proliferation",
                    weight=0.25,
                    contribution=0.0,
                    detail="0 distinct domain exposures detected.",
                ),
                RiskFactorDetail(
                    name="Breach & High-Risk Repositories",
                    weight=0.30,
                    contribution=0.0,
                    detail="No high-risk breach repositories identified.",
                ),
                RiskFactorDetail(
                    name="Forensic Completeness & Clustering",
                    weight=0.10,
                    contribution=0.0,
                    detail="0 sealed evidence artifacts.",
                ),
            ]
            return ExposureRiskEvaluation(
                risk_level=ExposureRiskLevel.LOW,
                internal_score=0.0,
                risk_policy_version=RISK_POLICY_VERSION,
                contributing_factors=factors,
                explanation="Zero verified exposure endpoints confirmed. Minimal exposure risk detected.",
                verified_count=0,
                unique_domains=0,
            )

        # Factor 1: Verified Findings Volume (weight: 35%)
        vol_score = min(100.0, verified_count * 10.0)
        vol_contrib = vol_score * 0.35
        factors.append(
            RiskFactorDetail(
                name="Verified Findings Volume",
                weight=0.35,
                contribution=round(vol_contrib, 2),
                detail=f"{verified_count} verified exposure endpoint(s) confirmed.",
            )
        )

        # Factor 2: Domain Spread & Proliferation (weight: 25%)
        spread_score = min(100.0, domain_count * 15.0)
        spread_contrib = spread_score * 0.25
        factors.append(
            RiskFactorDetail(
                name="Domain Spread & Proliferation",
                weight=0.25,
                contribution=round(spread_contrib, 2),
                detail=f"Discovered across {domain_count} distinct domain(s): {', '.join(unique_domains[:3])}{'...' if domain_count > 3 else ''}.",
            )
        )

        # Factor 3: Breach & High-Risk Repositories (weight: 30%)
        breach_score = 100.0 if has_breach_domain else 0.0
        breach_contrib = breach_score * 0.30
        factors.append(
            RiskFactorDetail(
                name="Breach & High-Risk Repositories",
                weight=0.30,
                contribution=round(breach_contrib, 2),
                detail="Presence detected in known breach/darknet index." if has_breach_domain else "No high-risk breach repositories identified.",
            )
        )

        # Factor 4: Forensic Completeness & Clustering (weight: 10%)
        cluster_score = min(100.0, cluster_count * 10.0)
        cluster_contrib = cluster_score * 0.10
        factors.append(
            RiskFactorDetail(
                name="Forensic Completeness & Clustering",
                weight=0.10,
                contribution=round(cluster_contrib, 2),
                detail=f"{evidence_complete_count}/{max(1, verified_count)} verified findings sealed across {cluster_count} cluster(s).",
            )
        )

        total_score = round(vol_contrib + spread_contrib + breach_contrib + cluster_contrib, 1)

        # Determine categorical risk level
        if total_score >= 80.0 or (has_breach_domain and verified_count >= 10):
            level = ExposureRiskLevel.CRITICAL
            explanation = "Critical exposure risk: Multiple verified public appearances and/or compromised breach repository indexing detected."
        elif total_score >= 60.0:
            level = ExposureRiskLevel.HIGH
            explanation = "High exposure risk: Significant multi-domain distribution of reference asset across public mirrors."
        elif total_score >= 25.0:
            level = ExposureRiskLevel.MEDIUM
            explanation = "Moderate exposure risk: Isolated verified public appearances detected with limited domain spread."
        else:
            level = ExposureRiskLevel.LOW
            explanation = "Low exposure risk: Minimal verified public occurrences identified."

        return ExposureRiskEvaluation(
            risk_level=level,
            internal_score=total_score,
            risk_policy_version=RISK_POLICY_VERSION,
            contributing_factors=factors,
            explanation=explanation,
            verified_count=verified_count,
            unique_domains=domain_count,
        )


exposure_risk_service = ExposureRiskService()
