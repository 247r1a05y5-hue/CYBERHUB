"""Rule Engine domain models and interfaces."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Callable, Dict, List, Optional


class RuleSeverity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


@dataclass
class RuleCondition:
    field_path: str  # e.g., "payload", "metadata.ip", "headers.User-Agent"
    operator: str    # "contains", "regex", "equals", "gt", "lt", "in", "startswith", "endswith"
    value: Any


@dataclass
class Rule:
    id: str
    name: str
    description: str
    severity: RuleSeverity
    weight: float = 10.0
    conditions: List[RuleCondition] = field(default_factory=list)
    condition_logic: str = "ALL"  # "ALL" (AND) or "ANY" (OR)
    tags: List[str] = field(default_factory=list)


@dataclass
class RuleMatch:
    rule_id: str
    name: str
    severity: RuleSeverity
    score_delta: float
    reason: str
    matched_field: str
    matched_value: Any


@dataclass
class RuleContext:
    payload: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, Any] = field(default_factory=dict)
    indicators: List[Dict[str, Any]] = field(default_factory=list)

    def get_field_value(self, path: str) -> Any:
        if path == "payload":
            return self.payload
        parts = path.split(".")
        root = parts[0]
        if root == "metadata":
            cur = self.metadata
        elif root == "features":
            cur = self.features
        else:
            cur = self.metadata.get(root)

        for p in parts[1:]:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return None
        return cur


@dataclass
class RuleExecutionResult:
    matched_rules: List[RuleMatch] = field(default_factory=list)
    total_score: float = 0.0
    rule_pack_version: str = "1.0.0"
    execution_time_ms: float = 0.0
