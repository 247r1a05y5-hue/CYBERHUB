"""Threat intelligence registry."""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from app.intel.base import ThreatIntelProvider, ThreatIntelResult
from app.intel.mock_provider import MockThreatIntelProvider


class ThreatIntelRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, ThreatIntelProvider] = {}

    def register(self, provider: ThreatIntelProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[ThreatIntelProvider]:
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())

    async def lookup_all(self, indicator_type: str, value: str) -> List[ThreatIntelResult]:
        tasks = [p.lookup(indicator_type, value) for p in self._providers.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid: List[ThreatIntelResult] = []
        for r in results:
            if isinstance(r, ThreatIntelResult):
                valid.append(r)
        return valid


_default_intel_registry: Optional[ThreatIntelRegistry] = None


def get_intel_registry() -> ThreatIntelRegistry:
    global _default_intel_registry
    if _default_intel_registry is None:
        _default_intel_registry = ThreatIntelRegistry()
        _default_intel_registry.register(MockThreatIntelProvider())
    return _default_intel_registry
