"""Threat intelligence provider interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ThreatIntelResult:
    provider: str
    indicator_type: str
    value: str
    is_malicious: bool
    reputation_score: float  # 0.0 (safe) to 100.0 (confirmed malicious)
    confidence: float        # 0.0 to 1.0
    threat_types: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


class ThreatIntelProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def lookup(self, indicator_type: str, value: str) -> Optional[ThreatIntelResult]:
        """Look up observable in provider feed."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check provider connectivity/health."""
        pass
