"""Analyzer base abstractions and context/finding models."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from app.models.analysis_result import Severity, Verdict


@dataclass
class ExtractedIndicator:
    indicator_type: str  # "ip_address", "domain", "url", "file_hash", etc.
    value: str
    confidence: float = 0.8
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisContext:
    analysis_id: uuid.UUID
    organization_id: uuid.UUID
    submitted_by_id: Optional[uuid.UUID]
    input_type: str
    payload: Optional[str] = None
    file_bytes: Optional[bytes] = None
    storage_ref: Optional[str] = None
    content_hash: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisFinding:
    analyzer_name: str
    verdict: Verdict
    severity: Severity
    risk_score: float  # 0.0 to 100.0
    confidence: float  # 0.0 to 1.0
    summary: str
    reasons: List[str] = field(default_factory=list)
    contributing_factors: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    indicators: List[ExtractedIndicator] = field(default_factory=list)
    model_version: Optional[str] = None
    rule_pack_version: Optional[str] = None
    policy_version: Optional[str] = None
    raw_findings: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: int = 0


class SecurityAnalyzer(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique analyzer plugin name."""
        pass

    @property
    @abstractmethod
    def supported_input_types(self) -> List[str]:
        """List of supported input types (e.g. ['text', 'url', 'file', 'email', 'json'])."""
        pass

    @abstractmethod
    async def analyze(self, context: AnalysisContext) -> AnalysisFinding:
        """
        Execute analysis pipeline:
        1. Preprocess & extract observables
        2. Evaluate RuleEngine
        3. Evaluate ModelRunner
        4. Query ThreatIntelRegistry
        5. Combine via RiskEngine
        6. Return AnalysisFinding
        """
        pass
