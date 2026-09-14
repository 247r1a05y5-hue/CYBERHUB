"""Unit tests for Rule Engine, Model Runner, and Risk Engine."""
import pytest

from app.ml.mock_runner import MockModelRunner
from app.models.analysis_result import Severity, Verdict
from app.risk.context import AssetCriticality, RiskContext
from app.risk.engine import RiskEngine
from app.risk.policy import RiskPolicy
from app.risk.signals import RiskSignal
from app.rules.base import Rule, RuleCondition, RuleContext, RuleSeverity
from app.rules.engine import RuleEngine


@pytest.mark.asyncio
async def test_rule_engine_execution():
    rule = Rule(
        id="R1",
        name="Suspicious Command Execution",
        description="Detects powershell execution",
        severity=RuleSeverity.high,
        weight=40.0,
        conditions=[
            RuleCondition(field_path="payload", operator="contains", value="powershell"),
        ],
    )
    engine = RuleEngine(rules=[rule])
    ctx = RuleContext(payload="executing powershell -enc JABz...")
    result = engine.execute(ctx)

    assert len(result.matched_rules) == 1
    assert result.matched_rules[0].rule_id == "R1"
    assert result.total_score == 40.0


@pytest.mark.asyncio
async def test_mock_model_runner():
    runner = MockModelRunner()
    features = {"text": "powershell -enc malware reverse_shell", "entropy": 7.2}
    result = await runner.predict(features)

    assert result.predicted_class == "malicious"
    assert result.risk_score >= 70.0
    assert result.confidence >= 0.8


@pytest.mark.asyncio
async def test_risk_engine_weighted_assessment():
    policy = RiskPolicy()
    engine = RiskEngine(policy=policy)

    signals = [
        RiskSignal(source="rules", name="Rules Match", raw_score=80.0, weight=1.0, confidence=0.9),
        RiskSignal(source="ml_model", name="Model Match", raw_score=90.0, weight=1.0, confidence=0.95),
        RiskSignal(source="threat_intel", name="Intel Hit", raw_score=100.0, weight=1.0, confidence=0.95),
    ]

    context = RiskContext(asset_criticality=AssetCriticality.critical, is_publicly_exposed=True)
    assessment = engine.assess(signals, context)

    assert assessment.final_score > 80.0
    assert assessment.severity == Severity.critical
    assert assessment.verdict == Verdict.malicious
    assert assessment.should_alert is True
    assert len(assessment.recommendations) > 0
