"""Deterministic mock analyzer combining Rules, ML Model, Intel, and Risk."""
from __future__ import annotations

import math
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
import uuid

from app.analyzers.base import AnalysisContext, AnalysisFinding, ExtractedIndicator, SecurityAnalyzer
from app.intel.registry import get_intel_registry
from app.ml.mock_runner import MockModelRunner
from app.risk.context import AssetCriticality, EnvironmentType, RiskContext
from app.risk.engine import RiskEngine
from app.risk.signals import RiskSignal
from app.rules.base import RuleContext
from app.rules.engine import RuleEngine
from app.rules.loader import RuleLoader


class MockAnalyzer(SecurityAnalyzer):
    def __init__(
        self,
        rule_pack_path: Optional[Path | str] = None,
        model_runner: Optional[MockModelRunner] = None,
        risk_engine: Optional[RiskEngine] = None,
    ) -> None:
        if rule_pack_path:
            self.rule_engine = RuleLoader.load_from_yaml(rule_pack_path)
        else:
            default_yaml = Path(__file__).parent.parent / "rules" / "packs" / "mock" / "rules.yaml"
            if default_yaml.exists():
                self.rule_engine = RuleLoader.load_from_yaml(default_yaml)
            else:
                self.rule_engine = RuleEngine()

        self.model_runner = model_runner or MockModelRunner()
        self.intel_registry = get_intel_registry()
        self.risk_engine = risk_engine or RiskEngine()

    @property
    def name(self) -> str:
        return "mock"

    @property
    def supported_input_types(self) -> List[str]:
        return ["text", "url", "file", "email", "ip", "domain", "hash", "json"]

    def _extract_indicators(self, text: str) -> List[ExtractedIndicator]:
        indicators: List[ExtractedIndicator] = []
        seen = set()

        # IP address regex
        ip_matches = re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", text)
        for ip in ip_matches:
            if ip not in seen and not ip.startswith("127."):
                seen.add(ip)
                indicators.append(ExtractedIndicator(indicator_type="ip_address", value=ip, confidence=0.9))

        # URL regex
        url_matches = re.findall(r"https?://[^\s<>\"'{}|\\^`]+", text)
        for url in url_matches:
            if url not in seen:
                seen.add(url)
                indicators.append(ExtractedIndicator(indicator_type="url", value=url, confidence=0.95))

        # Domain regex (from URLs or standalone)
        domain_matches = re.findall(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b", text)
        for dom in domain_matches:
            if dom not in seen and not dom.endswith(".local") and dom not in ("example.com", "localhost"):
                seen.add(dom)
                indicators.append(ExtractedIndicator(indicator_type="domain", value=dom, confidence=0.85))

        # Hashes (MD5, SHA1, SHA256)
        hash_matches = re.findall(r"\b([a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\b", text)
        for h in hash_matches:
            if h not in seen:
                seen.add(h)
                indicators.append(ExtractedIndicator(indicator_type="file_hash", value=h.lower(), confidence=0.99))

        return indicators

    def _calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        entropy = 0.0
        length = len(text)
        counts: Dict[str, int] = {}
        for c in text:
            counts[c] = counts.get(c, 0) + 1
        for count in counts.values():
            p = count / length
            entropy -= p * math.log2(p)
        return round(entropy, 2)

    async def analyze(self, context: AnalysisContext) -> AnalysisFinding:
        start_time = time.time()

        # 1. Resolve payload
        payload_text = context.payload or ""
        if context.file_bytes and not payload_text:
            try:
                payload_text = context.file_bytes.decode("utf-8", errors="ignore")
            except Exception:
                payload_text = str(context.file_bytes[:1000])

        # 2. Extract features and indicators
        indicators = self._extract_indicators(payload_text)
        entropy = self._calculate_entropy(payload_text)
        features = {
            "text": payload_text,
            "entropy": entropy,
            "payload_length": len(payload_text),
            "indicator_count": len(indicators),
        }

        # 3. Rule Engine Execution
        rule_ctx = RuleContext(
            payload=payload_text,
            metadata=context.raw_metadata,
            features=features,
            indicators=[{"type": i.indicator_type, "value": i.value} for i in indicators],
        )
        rule_result = self.rule_engine.execute(rule_ctx)

        # 4. ML Model Prediction
        model_result = await self.model_runner.predict(features)

        # 5. Threat Intel Lookups
        intel_hits = []
        max_intel_score = 0.0
        intel_reasons = []

        for ind in indicators:
            results = await self.intel_registry.lookup_all(ind.indicator_type, ind.value)
            for res in results:
                if res.is_malicious or res.reputation_score >= 50.0:
                    intel_hits.append(res)
                    max_intel_score = max(max_intel_score, res.reputation_score)
                    intel_reasons.append(
                        f"Threat intel feed '{res.provider}' flagged {ind.indicator_type} '{ind.value}' "
                        f"(Score: {res.reputation_score:.0f}, Types: {', '.join(res.threat_types) or 'unspecified'})"
                    )

        # 6. Assemble Signals for Risk Engine
        signals: List[RiskSignal] = []

        # Rule signal
        if rule_result.matched_rules:
            rule_reasons = [f"Rule match: {m.name} ({m.reason})" for m in rule_result.matched_rules]
            signals.append(
                RiskSignal(
                    source="rules",
                    name="Rule Engine Evaluation",
                    raw_score=min(100.0, rule_result.total_score),
                    weight=1.0,
                    confidence=0.95,
                    reasons=rule_reasons,
                    metadata={"matched_count": len(rule_result.matched_rules)},
                )
            )

        # ML model signal
        signals.append(
            RiskSignal(
                source="ml_model",
                name="Security Classifier Model",
                raw_score=model_result.risk_score,
                weight=1.0,
                confidence=model_result.confidence,
                reasons=model_result.explanation,
                metadata={"predicted_class": model_result.predicted_class, "probabilities": model_result.probabilities},
            )
        )

        # Threat intel signal
        if intel_hits:
            signals.append(
                RiskSignal(
                    source="threat_intel",
                    name="Threat Intelligence Correlation",
                    raw_score=max_intel_score,
                    weight=1.0,
                    confidence=0.90,
                    reasons=intel_reasons,
                    metadata={"hits_count": len(intel_hits)},
                )
            )

        # 7. Compute Risk Assessment
        env_str = str(context.options.get("environment", "production")).lower()
        crit_str = str(context.options.get("criticality", "medium")).lower()

        risk_ctx = RiskContext(
            asset_criticality=AssetCriticality(crit_str) if crit_str in AssetCriticality.__members__ else AssetCriticality.medium,
            environment=EnvironmentType(env_str) if env_str in EnvironmentType.__members__ else EnvironmentType.production,
            is_publicly_exposed=bool(context.options.get("public_facing", False)),
        )

        assessment = self.risk_engine.assess(signals, risk_ctx)
        exec_ms = int((time.time() - start_time) * 1000)

        raw_findings = {
            "features": features,
            "rule_matches": [
                {"id": m.rule_id, "name": m.name, "severity": m.severity.value, "score": m.score_delta}
                for m in rule_result.matched_rules
            ],
            "model_prediction": {
                "class": model_result.predicted_class,
                "confidence": model_result.confidence,
                "importances": model_result.feature_importances,
            },
            "threat_intel_hits": len(intel_hits),
        }

        return AnalysisFinding(
            analyzer_name=self.name,
            verdict=assessment.verdict,
            severity=assessment.severity,
            risk_score=assessment.final_score,
            confidence=assessment.confidence,
            summary=assessment.summary,
            reasons=assessment.reasons,
            contributing_factors=assessment.contributing_factors,
            recommendations=assessment.recommendations,
            indicators=indicators,
            model_version=self.model_runner.get_metadata().version,
            rule_pack_version=rule_result.rule_pack_version,
            policy_version=assessment.policy_version,
            raw_findings=raw_findings,
            execution_time_ms=exec_ms,
        )
