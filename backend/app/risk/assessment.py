"""Risk assessment output dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.models.analysis_result import Severity, Verdict


@dataclass
class RiskAssessment:
    final_score: float  # 0.0 to 100.0
    severity: Severity
    verdict: Verdict
    confidence: float
    policy_name: str
    policy_version: str
    should_alert: bool
    summary: str
    reasons: List[str] = field(default_factory=list)
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
