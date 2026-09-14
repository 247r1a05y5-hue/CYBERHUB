"""Risk Engine — Deterministic, explainable risk scoring without fabricated precision."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.case import Case, CaseStatus
from app.models.evidence import Evidence, VerificationStatus
from app.models.intelligence import RiskAssessment, RiskLevel
from app.services.audit_service import AuditService


class RiskService:
    """Service to compute deterministic risk assessments with explainable factor breakdowns."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_service = AuditService(session)

    async def compute_case_risk(
        self,
        case: Case,
        user_id: uuid.UUID | None = None,
    ) -> RiskAssessment:
        """
        Compute risk score deterministically from verified findings, domain uniqueness, and exposure categories.
        Identical inputs ALWAYS produce identical scores and factor explanations.
        """
        # Fetch verified evidence
        stmt = select(Evidence).where(
            Evidence.case_id == case.id,
            Evidence.verification_status == VerificationStatus.VERIFIED,
        )
        res = await self.session.execute(stmt)
        verified_items = list(res.scalars().all())

        verified_count = len(verified_items)
        unique_domains = len({item.domain for item in verified_items})
        has_darkweb = any("darkweb" in item.domain or "breach" in item.domain for item in verified_items)
        has_paste = any("paste" in item.domain for item in verified_items)

        # Base factor calculations
        score = 20.0  # Baseline
        factors: list[dict[str, Any]] = []

        if verified_count > 0:
            count_weight = min(35.0, verified_count * 7.0)
            score += count_weight
            factors.append({
                "name": "Verified Public Exposure Count",
                "weight": count_weight,
                "detail": f"{verified_count} verified exposure item(s) detected",
            })

        if unique_domains > 0:
            domain_weight = min(25.0, unique_domains * 5.0)
            score += domain_weight
            factors.append({
                "name": "Cross-Domain Propagation",
                "weight": domain_weight,
                "detail": f"Spanning {unique_domains} distinct top-level domains",
            })

        if has_darkweb:
            score += 20.0
            factors.append({
                "name": "High-Risk/Breach Forum Ingress",
                "weight": 20.0,
                "detail": "Appearance on breach repositories or illicit forums",
            })

        if has_paste:
            score += 10.0
            factors.append({
                "name": "Public Paste Repository Exposure",
                "weight": 10.0,
                "detail": "Raw credential or asset dump indexed on paste sites",
            })

        score = min(100.0, max(0.0, score))

        # Determine Discrete Risk Level
        if score >= 80.0:
            level = RiskLevel.CRITICAL
        elif score >= 60.0:
            level = RiskLevel.HIGH
        elif score >= 35.0:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        explanation = (
            f"{level.value} RISK — {verified_count} verified public exposures across {unique_domains} independent domains. "
            f"Risk elevated by presence on {'breach forums, ' if has_darkweb else ''}{'public paste sites' if has_paste else 'indexed web directories'}."
        )

        assessment = RiskAssessment(
            case_id=case.id,
            overall_risk_level=level,
            calculated_score=round(score, 1),
            factor_breakdown_json={"factors": factors, "verified_count": verified_count, "unique_domains": unique_domains},
            explanation_text=explanation,
            assessed_by_id=user_id,
        )
        self.session.add(assessment)

        case.status = CaseStatus.RISK_ASSESSED
        case.current_stage = 7
        await self.session.flush()

        # Audit risk calculation
        await self.audit_service.log(
            action=AuditAction.risk_calculated,
            user_id=user_id,
            organization_id=case.organization_id,
            resource_type="case",
            resource_id=str(case.id),
            details={
                "risk_level": level.value,
                "calculated_score": round(score, 1),
                "verified_count": verified_count,
            },
        )

        return assessment
