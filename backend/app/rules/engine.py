"""Rule evaluation engine."""
from __future__ import annotations

import re
import time
from typing import Any, List, Optional

from app.rules.base import (
    Rule,
    RuleCondition,
    RuleContext,
    RuleExecutionResult,
    RuleMatch,
    RuleSeverity,
)


class RuleEngine:
    def __init__(self, rules: Optional[List[Rule]] = None, version: str = "1.0.0") -> None:
        self.rules: List[Rule] = rules or []
        self.version = version

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def evaluate_condition(self, condition: RuleCondition, context: RuleContext) -> tuple[bool, Any]:
        val = context.get_field_value(condition.field_path)
        if val is None:
            return False, None

        op = condition.operator.lower()
        target = condition.value

        str_val = str(val)

        if op == "contains":
            if isinstance(target, list):
                match = any(str(t).lower() in str_val.lower() for t in target)
            else:
                match = str(target).lower() in str_val.lower()
            return match, val

        elif op == "regex":
            try:
                pattern = re.compile(str(target), re.IGNORECASE)
                match = bool(pattern.search(str_val))
                return match, val
            except re.error:
                return False, val

        elif op == "equals":
            return str_val.lower() == str(target).lower(), val

        elif op == "in":
            if isinstance(target, list):
                return str_val in target or any(str_val.lower() == str(t).lower() for t in target), val
            return False, val

        elif op == "startswith":
            return str_val.lower().startswith(str(target).lower()), val

        elif op == "endswith":
            return str_val.lower().endswith(str(target).lower()), val

        elif op == "gt":
            try:
                return float(val) > float(target), val
            except (ValueError, TypeError):
                return False, val

        elif op == "lt":
            try:
                return float(val) < float(target), val
            except (ValueError, TypeError):
                return False, val

        return False, val

    def evaluate_rule(self, rule: Rule, context: RuleContext) -> Optional[RuleMatch]:
        if not rule.conditions:
            return None

        matched_conditions = []
        last_matched_field = ""
        last_matched_val = None

        for cond in rule.conditions:
            matched, val = self.evaluate_condition(cond, context)
            if matched:
                matched_conditions.append(cond)
                last_matched_field = cond.field_path
                last_matched_val = val
            elif rule.condition_logic.upper() == "ALL":
                return None

        if rule.condition_logic.upper() == "ANY" and not matched_conditions:
            return None

        return RuleMatch(
            rule_id=rule.id,
            name=rule.name,
            severity=rule.severity,
            score_delta=rule.weight,
            reason=rule.description,
            matched_field=last_matched_field,
            matched_value=str(last_matched_val)[:100] if last_matched_val is not None else None,
        )

    def execute(self, context: RuleContext) -> RuleExecutionResult:
        start_time = time.time()
        matches: List[RuleMatch] = []
        total_score = 0.0

        for rule in self.rules:
            match = self.evaluate_rule(rule, context)
            if match:
                matches.append(match)
                total_score += match.score_delta

        exec_ms = (time.time() - start_time) * 1000.0
        return RuleExecutionResult(
            matched_rules=matches,
            total_score=total_score,
            rule_pack_version=self.version,
            execution_time_ms=exec_ms,
        )
