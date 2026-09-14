"""Risk Policy defining signal weights and threshold boundaries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from app.models.analysis_result import Severity, Verdict


@dataclass
class RiskPolicy:
    name: str = "default_policy"
    version: str = "1.0.0"
    description: str = "Standard balanced risk scoring policy"

    # Signal source weights (sum normalized automatically)
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "rules": 0.35,
            "ml_model": 0.35,
            "threat_intel": 0.20,
            "heuristic": 0.10,
        }
    )

    # Thresholds for severity mapping
    threshold_critical: float = 80.0
    threshold_high: float = 60.0
    threshold_medium: float = 35.0
    threshold_low: float = 15.0

    # Minimum risk score to trigger an Alert
    alert_creation_threshold: float = 40.0

    def get_severity(self, score: float) -> Severity:
        if score >= self.threshold_critical:
            return Severity.critical
        elif score >= self.threshold_high:
            return Severity.high
        elif score >= self.threshold_medium:
            return Severity.medium
        elif score >= self.threshold_low:
            return Severity.low
        return Severity.info

    def get_verdict(self, score: float, confidence: float) -> Verdict:
        if score >= self.threshold_high:
            return Verdict.malicious
        elif score >= self.threshold_medium:
            return Verdict.suspicious
        elif score < self.threshold_low and confidence >= 0.5:
            return Verdict.benign
        return Verdict.suspicious if score >= self.threshold_low else Verdict.benign
