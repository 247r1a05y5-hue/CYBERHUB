"""Rule pack YAML loader."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import yaml

from app.rules.base import Rule, RuleCondition, RuleSeverity
from app.rules.engine import RuleEngine


class RuleLoader:
    @staticmethod
    def load_from_yaml(file_path: Path | str) -> RuleEngine:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Rule pack not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        pack_name = data.get("name", "unnamed_pack")
        version = data.get("version", "1.0.0")
        raw_rules = data.get("rules", [])

        rules: List[Rule] = []
        for r in raw_rules:
            conditions = [
                RuleCondition(
                    field_path=c["field"],
                    operator=c["operator"],
                    value=c["value"],
                )
                for c in r.get("conditions", [])
            ]
            rules.append(
                Rule(
                    id=r["id"],
                    name=r["name"],
                    description=r.get("description", r["name"]),
                    severity=RuleSeverity(r.get("severity", "medium").lower()),
                    weight=float(r.get("weight", 10.0)),
                    conditions=conditions,
                    condition_logic=r.get("condition_logic", "ALL"),
                    tags=r.get("tags", []),
                )
            )

        return RuleEngine(rules=rules, version=version)
