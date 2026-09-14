"""Risk calculation engine."""
from __future__ import annotations

from typing import List, Optional

from app.models.analysis_result import Severity, Verdict
from app.risk.assessment import RiskAssessment
from app.risk.context import RiskContext
from app.risk.policy import RiskPolicy
from app.risk.signals import RiskSignal


class RiskEngine:
    def __init__(self, policy: Optional[RiskPolicy] = None) -> None:
        self.policy = policy or RiskPolicy()

    def assess(
        self,
        signals: List[RiskSignal],
        context: Optional[RiskContext] = None,
    ) -> RiskAssessment:
        ctx = context or RiskContext()
        policy = self.policy

        if not signals:
            return RiskAssessment(
                final_score=0.0,
                severity=Severity.info,
                verdict=Verdict.benign,
                confidence=1.0,
                policy_name=policy.name,
                policy_version=policy.version,
                should_alert=False,
                summary="No risk signals detected. Item evaluated as benign.",
                reasons=["No indicators or rule triggers identified."],
                recommendations=["No action required."],
            )

        # Normalize weights
        total_weight = 0.0
        weighted_score_sum = 0.0
        confidence_sum = 0.0

        all_reasons: List[str] = []
        contributing_factors = []

        for signal in signals:
            source_weight = policy.weights.get(signal.source, 0.1) * signal.weight
            weighted_score_sum += signal.raw_score * source_weight * signal.confidence
            total_weight += source_weight
            confidence_sum += signal.confidence * source_weight

            all_reasons.extend(signal.reasons)
            contributing_factors.append({
                "source": signal.source,
                "name": signal.name,
                "raw_score": signal.raw_score,
                "confidence": signal.confidence,
                "reasons": signal.reasons,
            })

        base_score = (weighted_score_sum / total_weight) if total_weight > 0 else 0.0
        avg_confidence = (confidence_sum / total_weight) if total_weight > 0 else 0.5

        # Apply environmental context multiplier
        multiplier = ctx.get_multiplier()
        final_score = min(100.0, max(0.0, base_score * multiplier))

        severity = policy.get_severity(final_score)
        verdict = policy.get_verdict(final_score, avg_confidence)
        should_alert = final_score >= policy.alert_creation_threshold

        # Generate actionable SOC recommendations
        recommendations = self._generate_recommendations(verdict, severity, final_score, ctx)

        summary = (
            f"Evaluated as {verdict.value.upper()} (Risk Score: {final_score:.1f}/100, "
            f"Severity: {severity.value.upper()}) based on {len(signals)} signals."
        )

        return RiskAssessment(
            final_score=round(final_score, 2),
            severity=severity,
            verdict=verdict,
            confidence=round(avg_confidence, 2),
            policy_name=policy.name,
            policy_version=policy.version,
            should_alert=should_alert,
            summary=summary,
            reasons=list(dict.fromkeys(all_reasons)),  # deduplicate preserving order
            contributing_factors=contributing_factors,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        verdict: Verdict,
        severity: Severity,
        score: float,
        context: RiskContext,
    ) -> List[str]:
        recs: List[str] = []
        if verdict == Verdict.malicious:
            recs.append("Isolate affected endpoints/assets immediately from the network.")
            recs.append("Revoke active user sessions and reset credentials.")
            recs.append("Block related domains/IPs at the perimeter firewall / DNS firewall.")
            recs.append("Initiate standard Incident Response triage workflow.")
        elif verdict == Verdict.suspicious:
            recs.append("Review detailed telemetry and indicator sighting logs.")
            recs.append("Place affected entity under enhanced monitoring.")
            recs.append("Verify user authenticity via out-of-band communication.")
        else:
            recs.append("No immediate containment necessary.")
            recs.append("Log sighting event for baseline telemetry.")

        if context.is_publicly_exposed:
            recs.append("Audit public-facing ingress rules and WAF configurations.")

        return recs
