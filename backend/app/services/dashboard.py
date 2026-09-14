"""Dashboard service for aggregating operational metrics and trends."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus
from app.models.analysis import Analysis, AnalysisStatus
from app.models.analysis_result import AnalysisResult, Severity
from app.models.incident import Incident, IncidentStatus
from app.models.indicator import Indicator
from app.schemas.dashboard import (
    DashboardMetrics,
    SeverityCount,
    StatusCount,
    TopIndicator,
    TrendPoint,
)


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_metrics(self, organization_id: uuid.UUID) -> DashboardMetrics:
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)

        # 1. Core counters
        total_analyses = (
            await self.session.execute(
                select(func.count(Analysis.id)).where(Analysis.organization_id == organization_id)
            )
        ).scalar_one()

        total_alerts = (
            await self.session.execute(
                select(func.count(Alert.id)).where(Alert.organization_id == organization_id)
            )
        ).scalar_one()

        open_alerts = (
            await self.session.execute(
                select(func.count(Alert.id)).where(
                    Alert.organization_id == organization_id,
                    Alert.status.in_([AlertStatus.open, AlertStatus.acknowledged]),
                )
            )
        ).scalar_one()

        total_incidents = (
            await self.session.execute(
                select(func.count(Incident.id)).where(Incident.organization_id == organization_id)
            )
        ).scalar_one()

        active_incidents = (
            await self.session.execute(
                select(func.count(Incident.id)).where(
                    Incident.organization_id == organization_id,
                    Incident.status.notin_([IncidentStatus.resolved, IncidentStatus.closed]),
                )
            )
        ).scalar_one()

        critical_alerts_24h = (
            await self.session.execute(
                select(func.count(Alert.id)).where(
                    Alert.organization_id == organization_id,
                    Alert.severity == Severity.critical,
                    Alert.created_at >= yesterday,
                )
            )
        ).scalar_one()

        avg_risk = (
            await self.session.execute(
                select(func.avg(AnalysisResult.risk_score))
                .join(Analysis, AnalysisResult.analysis_id == Analysis.id)
                .where(Analysis.organization_id == organization_id)
            )
        ).scalar_one() or 0.0

        # 2. Analyses by status
        analysis_status_res = await self.session.execute(
            select(Analysis.status, func.count(Analysis.id))
            .where(Analysis.organization_id == organization_id)
            .group_by(Analysis.status)
        )
        analyses_by_status = [
            StatusCount(status=row[0].value if hasattr(row[0], "value") else str(row[0]), count=row[1])
            for row in analysis_status_res.all()
        ]

        # 3. Alerts by severity
        alert_sev_res = await self.session.execute(
            select(Alert.severity, func.count(Alert.id))
            .where(Alert.organization_id == organization_id)
            .group_by(Alert.severity)
        )
        alerts_by_severity = [
            SeverityCount(severity=row[0].value if hasattr(row[0], "value") else str(row[0]), count=row[1])
            for row in alert_sev_res.all()
        ]

        # 4. Incidents by status
        inc_status_res = await self.session.execute(
            select(Incident.status, func.count(Incident.id))
            .where(Incident.organization_id == organization_id)
            .group_by(Incident.status)
        )
        incidents_by_status = [
            StatusCount(status=row[0].value if hasattr(row[0], "value") else str(row[0]), count=row[1])
            for row in inc_status_res.all()
        ]

        # 5. 7-Day Activity Trend
        trend_points: List[TrendPoint] = []
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_count = (
                await self.session.execute(
                    select(func.count(Analysis.id)).where(
                        Analysis.organization_id == organization_id,
                        Analysis.created_at >= day_start,
                        Analysis.created_at < day_end,
                    )
                )
            ).scalar_one()

            trend_points.append(
                TrendPoint(
                    timestamp=day_start.strftime("%b %d"),
                    count=day_count,
                    critical=0,
                    high=0,
                    medium=0,
                    low=0,
                )
            )

        # 6. Top Indicators
        indicators_res = await self.session.execute(
            select(Indicator.indicator_type, Indicator.value, func.count(Indicator.id), func.avg(Indicator.confidence))
            .where(Indicator.organization_id == organization_id)
            .group_by(Indicator.indicator_type, Indicator.value)
            .order_by(desc(func.count(Indicator.id)))
            .limit(5)
        )
        top_indicators = [
            TopIndicator(
                type=row[0].value if hasattr(row[0], "value") else str(row[0]),
                value=row[1],
                sightings=row[2],
                confidence=float(row[3] or 0.8),
            )
            for row in indicators_res.all()
        ]

        # 7. Recent Alerts
        recent_alerts_res = await self.session.execute(
            select(Alert)
            .where(Alert.organization_id == organization_id)
            .order_by(desc(Alert.created_at))
            .limit(5)
        )
        recent_alerts = [
            {
                "id": str(a.id),
                "title": a.title,
                "severity": a.severity.value,
                "status": a.status.value,
                "created_at": a.created_at.isoformat(),
            }
            for a in recent_alerts_res.scalars().all()
        ]

        # 8. Recent Incidents
        recent_inc_res = await self.session.execute(
            select(Incident)
            .where(Incident.organization_id == organization_id)
            .order_by(desc(Incident.created_at))
            .limit(5)
        )
        recent_incidents = [
            {
                "id": str(inc.id),
                "title": inc.title,
                "severity": inc.severity.value,
                "status": inc.status.value,
                "created_at": inc.created_at.isoformat(),
            }
            for inc in recent_inc_res.scalars().all()
        ]

        return DashboardMetrics(
            total_analyses=total_analyses,
            total_alerts=total_alerts,
            open_alerts=open_alerts,
            total_incidents=total_incidents,
            active_incidents=active_incidents,
            critical_alerts_24h=critical_alerts_24h,
            average_risk_score=round(avg_risk, 1),
            analyses_by_status=analyses_by_status,
            alerts_by_severity=alerts_by_severity,
            incidents_by_status=incidents_by_status,
            activity_trend_7d=trend_points,
            top_indicators=top_indicators,
            recent_alerts=recent_alerts,
            recent_incidents=recent_incidents,
        )
