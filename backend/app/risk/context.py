"""Risk Context representing environmental and asset factors."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class AssetCriticality(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class EnvironmentType(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"


@dataclass
class RiskContext:
    asset_criticality: AssetCriticality = AssetCriticality.medium
    environment: EnvironmentType = EnvironmentType.production
    is_publicly_exposed: bool = False
    is_privileged_user: bool = False
    tags: Dict[str, Any] = field(default_factory=dict)

    def get_multiplier(self) -> float:
        mult = 1.0
        if self.asset_criticality == AssetCriticality.critical:
            mult *= 1.3
        elif self.asset_criticality == AssetCriticality.high:
            mult *= 1.15
        elif self.asset_criticality == AssetCriticality.low:
            mult *= 0.85

        if self.is_publicly_exposed:
            mult *= 1.15

        if self.is_privileged_user:
            mult *= 1.10

        if self.environment == EnvironmentType.development:
            mult *= 0.90

        return mult
