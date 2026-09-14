"""Risk signals from pipeline stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RiskSignal:
    source: str  # "rules", "ml_model", "threat_intel", "heuristic"
    name: str
    raw_score: float  # 0.0 to 100.0
    weight: float = 1.0
    confidence: float = 1.0  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
