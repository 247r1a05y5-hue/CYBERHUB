"""Report generation service for analyses and incidents."""
from __future__ import annotations

from datetime import datetime, timezone
import html
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.audit_log import AuditAction
from app.models.notification import NotificationType
from app.models.report import Report, ReportFormat, ReportStatus
from app.repositories.analysis import AnalysisRepository
from app.repositories.incident import IncidentRepository
from app.repositories.report import ReportRepository
from app.schemas.report import ReportGenerateRequest
from app.services.audit import AuditService
from app.services.notification import NotificationService
from app.storage.backend import get_storage


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReportRepository(session)
        self.analysis_repo = AnalysisRepository(session)
        self.incident_repo = IncidentRepository(session)
        self.audit = AuditService(session)
        self.notification = NotificationService(session)
        self.storage = get_storage()

    async def get_report(self, report_id: uuid.UUID, organization_id: uuid.UUID) -> Report:
        report = await self.repo.get_with_details(report_id, organization_id)
        if not report:
            raise NotFoundError(f"Report {report_id} not found")
        return report

    async def list_reports(
        self,
        organization_id: uuid.UUID,
        incident_id: Optional[uuid.UUID] = None,
        analysis_id: Optional[uuid.UUID] = None,
        status: Optional[ReportStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Report], int]:
        return await self.repo.list_by_org(
            organization_id=organization_id,
            incident_id=incident_id,
            analysis_id=analysis_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def generate_report(
        self,
        organization_id: uuid.UUID,
        request: ReportGenerateRequest,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Report:
        if not request.analysis_id and not request.incident_id:
            raise ValidationError("Report must reference an analysis or incident")

        # Create pending report entry
        report = await self.repo.create(
            organization_id=organization_id,
            created_by_id=actor_id,
            analysis_id=request.analysis_id,
            incident_id=request.incident_id,
            title=request.title,
            format=request.format,
            status=ReportStatus.generating,
        )

        try:
            markdown_content = ""
            if request.analysis_id:
                analysis = await self.analysis_repo.get_with_details(request.analysis_id, organization_id)
                if not analysis:
                    raise NotFoundError(f"Analysis {request.analysis_id} not found")
                markdown_content = self._render_analysis_markdown(analysis, request.title, request.custom_notes)

            elif request.incident_id:
                incident = await self.incident_repo.get_with_details(request.incident_id, organization_id)
                if not incident:
                    raise NotFoundError(f"Incident {request.incident_id} not found")
                markdown_content = self._render_incident_markdown(incident, request.title, request.custom_notes)

            final_content = markdown_content
            if request.format == ReportFormat.html:
                final_content = self._render_html_wrapper(request.title, markdown_content)

            # Save report content
            storage_path, _, _, _ = await self.storage.save(
                content=final_content.encode("utf-8"),
                filename=f"report_{report.id}.{request.format.value}",
                subfolder="reports",
            )

            report.content = final_content
            report.storage_path = storage_path
            report.status = ReportStatus.ready
            await self.session.flush()

            await self.audit.log(
                organization_id=organization_id,
                action=AuditAction.create,
                target_type="report",
                target_id=str(report.id),
                user_id=actor_id,
                details={"title": report.title, "format": report.format.value},
            )

            if actor_id:
                await self.notification.create_notification(
                    organization_id=organization_id,
                    user_id=actor_id,
                    title=f"Report Ready: {report.title}",
                    message=f"Your security report '{report.title}' has been generated.",
                    notification_type=NotificationType.report_ready,
                    entity_type="report",
                    entity_id=str(report.id),
                )

            return report

        except Exception as e:
            report.status = ReportStatus.failed
            report.error_message = str(e)
            await self.session.flush()
            raise

    def _render_analysis_markdown(self, analysis: Any, title: str, custom_notes: Optional[str]) -> str:
        res = analysis.result
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        md = [
            f"# {title}",
            f"**Generated:** {ts} | **Analysis ID:** `{analysis.id}` | **Status:** `{analysis.status.value.upper()}`",
            "",
            "## Executive Summary",
        ]

        if res:
            md.extend([
                f"- **Verdict:** `{res.verdict.value.upper()}`",
                f"- **Severity:** `{res.severity.value.upper()}`",
                f"- **Risk Score:** `{res.risk_score:.1f} / 100.0`",
                f"- **Confidence:** `{res.confidence * 100.0:.0f}%`",
                f"- **Summary:** {res.summary or 'N/A'}",
                "",
                "## Key Reasons & Observations",
            ])
            for r in (res.reasons or []):
                md.append(f"- {r}")

            if res.recommendations:
                md.extend(["", "## SOC Recommendations"])
                for rec in res.recommendations:
                    md.append(f"1. {rec}")

            if res.indicators:
                md.extend(["", "## Extracted Indicators of Compromise (IoCs)"])
                md.append("| Type | Value | Confidence |")
                md.append("|---|---|---|")
                for ind in res.indicators:
                    if isinstance(ind, dict):
                        md.append(f"| `{ind.get('type')}` | `{ind.get('value')}` | {ind.get('confidence', 'N/A')} |")

        if custom_notes:
            md.extend(["", "## Analyst Notes", custom_notes])

        return "\n".join(md)

    def _render_incident_markdown(self, incident: Any, title: str, custom_notes: Optional[str]) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        md = [
            f"# {title}",
            f"**Generated:** {ts} | **Incident ID:** `{incident.id}`",
            "",
            "## Incident Overview",
            f"- **Title:** {incident.title}",
            f"- **Severity:** `{incident.severity.value.upper()}`",
            f"- **Current Status:** `{incident.status.value.upper()}`",
            f"- **Description:** {incident.description or 'None provided.'}",
            "",
            "## Linked Alerts",
        ]

        if incident.alert_links:
            md.append("| Severity | Title | Status | Created |")
            md.append("|---|---|---|---|")
            for link in incident.alert_links:
                a = link.alert
                if a:
                    md.append(f"| `{a.severity.value.upper()}` | {a.title} | `{a.status.value}` | {a.created_at.strftime('%Y-%m-%d %H:%M')} |")
        else:
            md.append("No alerts linked.")

        if incident.notes:
            md.extend(["", "## Investigation Activity Log"])
            for n in incident.notes:
                author_str = n.author.email if n.author else "System"
                md.append(f"- **{n.created_at.strftime('%Y-%m-%d %H:%M:%S')}** ({author_str}): {n.content}")

        if custom_notes:
            md.extend(["", "## Additional Notes", custom_notes])

        return "\n".join(md)

    def _render_html_wrapper(self, title: str, markdown_content: str) -> str:
        escaped_md = html.escape(markdown_content)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1e293b; background: #f8fafc; }}
        .report-card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 32px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
        h1, h2, h3 {{ color: #0f172a; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 10px 12px; text-align: left; }}
        th {{ background-color: #f1f5f9; }}
        code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
        pre {{ background: #0f172a; color: #f8fafc; padding: 16px; border-radius: 6px; overflow-x: auto; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="report-card">
        <pre>{escaped_md}</pre>
    </div>
</body>
</html>"""
