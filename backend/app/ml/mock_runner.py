"""Deterministic MockModelRunner for testing and development."""
from __future__ import annotations

import time
from typing import Any, Dict

from app.ml.base import ModelHealth, ModelMetadata, ModelResult, ModelRunner


class MockModelRunner(ModelRunner):
    """
    Deterministic mock model runner that inspects keyword features
    to produce explainable test predictions.
    """

    def __init__(self, version: str = "v1.0.0-mock") -> None:
        self.version = version

    def get_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            name="MockSecurityClassifier",
            version=self.version,
            description="Deterministic mock classifier for platform validation",
            framework="heuristic-mock",
            input_types=["text", "url", "file", "json"],
        )

    async def predict(self, features: Dict[str, Any]) -> ModelResult:
        start_time = time.time()
        
        # Analyze input features
        text_content = str(features.get("text", "")).lower()
        has_suspicious_patterns = any(
            k in text_content for k in ["malware", "exploit", "cve-", "eval(", "cmd.exe", "powershell -enc", "phish", "steal", "reverse_shell"]
        )
        has_benign_patterns = any(
            k in text_content for k in ["normal", "safe", "welcome", "documentation", "health check"]
        )

        entropy = float(features.get("entropy", 3.0))
        high_entropy = entropy > 6.5

        risk_score = 10.0
        confidence = 0.85
        explanations = []
        feature_importances: Dict[str, float] = {}

        if has_suspicious_patterns:
            risk_score += 65.0
            confidence = 0.95
            explanations.append("Matched known suspicious attack keywords in payload")
            feature_importances["suspicious_keywords"] = 0.70

        if high_entropy:
            risk_score += 20.0
            explanations.append(f"High payload entropy detected ({entropy:.2f})")
            feature_importances["entropy"] = 0.25

        if has_benign_patterns and not has_suspicious_patterns:
            risk_score = max(5.0, risk_score - 10.0)
            explanations.append("Payload matches standard benign traffic characteristics")
            feature_importances["benign_signature"] = 0.80

        risk_score = min(100.0, max(0.0, risk_score))
        
        if risk_score >= 70.0:
            predicted_class = "malicious"
        elif risk_score >= 35.0:
            predicted_class = "suspicious"
        else:
            predicted_class = "benign"

        probs = {
            "benign": max(0.01, round(1.0 - (risk_score / 100.0), 2)),
            "malicious": max(0.01, round(risk_score / 100.0, 2)),
        }
        # Normalize probabilities
        total_p = probs["benign"] + probs["malicious"]
        probs["benign"] /= total_p
        probs["malicious"] /= total_p

        return ModelResult(
            predicted_class=predicted_class,
            risk_score=risk_score,
            confidence=confidence,
            probabilities=probs,
            feature_importances=feature_importances,
            explanation=explanations,
            raw_output={"features_evaluated": len(features), "mock": True},
        )

    async def health_check(self) -> ModelHealth:
        return ModelHealth(is_healthy=True, status="ready", latency_ms=1.2)
