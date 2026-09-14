"""Analyzer registry for discovering and executing security analyzers."""
from __future__ import annotations

from typing import Dict, List, Optional

from app.analyzers.base import SecurityAnalyzer
from app.analyzers.mock_analyzer import MockAnalyzer


class AnalyzerRegistry:
    def __init__(self) -> None:
        self._analyzers: Dict[str, SecurityAnalyzer] = {}
        self._input_type_map: Dict[str, str] = {}

    def register(self, analyzer: SecurityAnalyzer, is_default_for: Optional[List[str]] = None) -> None:
        self._analyzers[analyzer.name] = analyzer
        for input_type in (is_default_for or analyzer.supported_input_types):
            self._input_type_map[input_type] = analyzer.name

    def get(self, name: str) -> Optional[SecurityAnalyzer]:
        return self._analyzers.get(name)

    def get_for_input_type(self, input_type: str) -> Optional[SecurityAnalyzer]:
        analyzer_name = self._input_type_map.get(input_type)
        if analyzer_name:
            return self._analyzers.get(analyzer_name)
        return self._analyzers.get("mock")

    def list_analyzers(self) -> List[str]:
        return list(self._analyzers.keys())


_default_analyzer_registry: Optional[AnalyzerRegistry] = None


def get_analyzer_registry() -> AnalyzerRegistry:
    global _default_analyzer_registry
    if _default_analyzer_registry is None:
        _default_analyzer_registry = AnalyzerRegistry()
        _default_analyzer_registry.register(MockAnalyzer())
    return _default_analyzer_registry
