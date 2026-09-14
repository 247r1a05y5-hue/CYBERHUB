"""Dashboard metrics & aggregations schemas."""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class SeverityCount(BaseModel):
    severity: str
    count: int


class StatusCount(BaseModel):
    status: str
    count: int


class TrendPoint(BaseModel):
    timestamp: str
    count: int
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class TopIndicator(BaseModel):
    type: str
    value: str
    sightings: int
    confidence: float


class DashboardMetrics(BaseModel):
    total_analyses: int
    total_alerts: int
    open_alerts: int
    total_incidents: int
    active_incidents: int
    critical_alerts_24h: int
    average_risk_score: float
    analyses_by_status: List[StatusCount]
    alerts_by_severity: List[SeverityCount]
    incidents_by_status: List[StatusCount]
    activity_trend_7d: List[TrendPoint]
    top_indicators: List[TopIndicator]
    recent_alerts: List[Dict[str, Any]]
    recent_incidents: List[Dict[str, Any]]
