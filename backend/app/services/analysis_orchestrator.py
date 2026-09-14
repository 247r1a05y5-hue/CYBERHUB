"""Analysis Orchestrator service."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid

import redis.asyncio as aioredis
from rq import Queue
import redis as syncredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzers.base import AnalysisContext, AnalysisFinding
from app.analyzers.registry import get_analyzer_registry
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.alert import AlertSeverity
from app.models.analysis import Analysis, AnalysisStatus
from app.models.analysis_input import AnalysisInput, InputType
from app.models.analysis_result import AnalysisResult, Severity, Verdict
from app.models.audit_log import AuditAction
from app.models.indicator import Indicator, IndicatorType
from app.models.notification import NotificationType
from app.repositories.analysis import (
    AnalysisInputRepository,
    AnalysisRepository,
    AnalysisResultRepository,
)
from app.repositories.indicator import IndicatorRepository
from app.schemas.alert import AlertCreate
from app.schemas.analysis import AnalysisSubmissionRequest
from app.services.alert import AlertService
from app.services.audit import AuditService
from app.services.notification import NotificationService
from app.storage.backend import get_storage

settings = get_settings()


class AnalysisOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AnalysisRepository(session)
        self.input_repo = AnalysisInputRepository(session)
        self.result_repo = AnalysisResultRepository(session)
        self.indicator_repo = IndicatorRepository(session)
        self.alert_service = AlertService(session)
        self.audit_service = AuditService(session)
        self.notification_service = NotificationService(session)
        self.storage = get_storage()
        self.registry = get_analyzer_registry()

    async def submit_analysis(
        self,
        organization_id: uuid.UUID,
        request: AnalysisSubmissionRequest,
        file_bytes: Optional[bytes] = None,
        original_filename: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Analysis:
        payload = request.payload or ""
        sha256_hash: Optional[str] = None
        storage_ref: Optional[str] = None

        if file_bytes is not None:
            storage_ref, sha256_hash, _, _ = await self.storage.save(
                content=file_bytes,
                filename=original_filename,
                subfolder="analyses",
            )
        elif payload:
            sha256_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        # Idempotency check: if identical hash recently completed/queued, reuse
        if sha256_hash:
            existing = await self.repo.find_by_content_hash(organization_id, sha256_hash)
            if existing and existing.status in (AnalysisStatus.completed, AnalysisStatus.running, AnalysisStatus.queued):
                return existing

        # Create Analysis row
        analysis = await self.repo.create(
            organization_id=organization_id,
            created_by_id=actor_id,
            analyzer_type=request.analyzer_type,
            status=AnalysisStatus.queued,
            content_hash=sha256_hash,
            tags=request.options or {},
        )

        # Create AnalysisInput row
        await self.input_repo.create(
            analysis_id=analysis.id,
            input_type=request.input_type,
            storage_ref=storage_ref,
            raw_metadata={
                **(request.raw_metadata or {}),
                "original_filename": original_filename,
                "payload_snippet": payload[:200] if payload else None,
            },
            sha256=sha256_hash,
        )

        await self.audit_service.log(
            organization_id=organization_id,
            action=AuditAction.create,
            target_type="analysis",
            target_id=str(analysis.id),
            user_id=actor_id,
            details={"analyzer": analysis.analyzer_type, "input_type": request.input_type.value},
        )

        # Enqueue job via Redis RQ or fallback to immediate sync run
        try:
            r_conn = syncredis.from_url(settings.REDIS_URL)
            q = Queue("analyses", connection=r_conn)
            job = q.enqueue("app.workers.jobs.run_analysis_job", str(analysis.id))
            analysis.job_id = job.id
            await self.session.flush()
        except Exception:
            # If Redis RQ unavailable in local test, run pipeline synchronously
            await self.run_pipeline(analysis.id, payload=payload, file_bytes=file_bytes)

        return await self.repo.get_with_details(analysis.id, organization_id)  # type: ignore[return-value]

    async def run_pipeline(
        self,
        analysis_id: uuid.UUID,
        payload: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
    ) -> AnalysisFinding:
        analysis = await self.repo.get_by_id(analysis_id)
        if not analysis:
            raise NotFoundError(f"Analysis {analysis_id} not found")

        # Update status -> running
        await self.repo.update_status(analysis_id, AnalysisStatus.running)
        await self._publish_event(analysis.organization_id, analysis_id, {"status": "running", "message": "Analysis started"})

        try:
            # Get input details
            inp = await self.input_repo.get_by_analysis_id(analysis_id)
            if not inp:
                raise ValidationError("Missing analysis input")

            if inp.storage_ref and not file_bytes:
                try:
                    file_bytes = await self.storage.read(inp.storage_ref)
                except Exception:
                    file_bytes = None

            # Resolve Analyzer
            analyzer = self.registry.get(analysis.analyzer_type) or self.registry.get_for_input_type(inp.input_type.value)
            if not analyzer:
                analyzer = self.registry.get("mock")
                if not analyzer:
                    raise ValidationError(f"No suitable analyzer found for {analysis.analyzer_type}")

            context = AnalysisContext(
                analysis_id=analysis.id,
                organization_id=analysis.organization_id,
                submitted_by_id=analysis.created_by_id,
                input_type=inp.input_type.value,
                payload=payload or (inp.raw_metadata or {}).get("payload_snippet"),
                file_bytes=file_bytes,
                storage_ref=inp.storage_ref,
                content_hash=inp.sha256,
                raw_metadata=inp.raw_metadata or {},
                options=analysis.tags or {},
            )

            # Execute Analyzer
            finding: AnalysisFinding = await analyzer.analyze(context)

            # Persist AnalysisResult
            await self.result_repo.create(
                analysis_id=analysis.id,
                verdict=finding.verdict,
                severity=finding.severity,
                risk_score=finding.risk_score,
                confidence=finding.confidence,
                summary=finding.summary,
                reasons=finding.reasons,
                contributing_factors=finding.contributing_factors,
                recommendations=finding.recommendations,
                indicators=[
                    {"type": i.indicator_type, "value": i.value, "confidence": i.confidence}
                    for i in finding.indicators
                ],
                model_version=finding.model_version,
                rule_pack_version=finding.rule_pack_version,
                policy_version=finding.policy_version,
                raw_findings=finding.raw_findings,
                execution_time_ms=finding.execution_time_ms,
            )

            # Persist Indicators
            for ind in finding.indicators:
                ind_type = IndicatorType(ind.indicator_type) if ind.indicator_type in IndicatorType.__members__ else IndicatorType.other
                await self.indicator_repo.create(
                    organization_id=analysis.organization_id,
                    analysis_id=analysis.id,
                    indicator_type=ind_type,
                    value=ind.value,
                    confidence=ind.confidence,
                    context=ind.context,
                )

            # Auto create Alert if high risk or malicious/suspicious
            if finding.risk_score >= 40.0 or finding.severity in (Severity.high, Severity.critical):
                alert_sev = finding.severity
                await self.alert_service.create_alert(
                    organization_id=analysis.organization_id,
                    alert_in=AlertCreate(
                        analysis_id=analysis.id,
                        title=f"{finding.verdict.value.upper()} Detection: {finding.summary[:100]}",
                        description=finding.summary,
                        severity=alert_sev,
                        risk_score=finding.risk_score,
                    ),
                    actor_id=analysis.created_by_id,
                )

            # Mark completed
            await self.repo.update_status(
                analysis_id=analysis.id,
                status=AnalysisStatus.completed,
                execution_time_ms=finding.execution_time_ms,
            )

            # Notify user
            if analysis.created_by_id:
                await self.notification_service.create_notification(
                    organization_id=analysis.organization_id,
                    user_id=analysis.created_by_id,
                    title=f"Analysis Complete: {finding.verdict.value.upper()}",
                    message=f"Analysis completed with risk score {finding.risk_score:.1f} ({finding.severity.value.upper()})",
                    notification_type=NotificationType.analysis_completed,
                    entity_type="analysis",
                    entity_id=str(analysis.id),
                )

            # Publish SSE completion event
            await self._publish_event(
                analysis.organization_id,
                analysis.id,
                {
                    "status": "completed",
                    "verdict": finding.verdict.value,
                    "severity": finding.severity.value,
                    "risk_score": finding.risk_score,
                    "execution_time_ms": finding.execution_time_ms,
                },
            )

            return finding

        except Exception as err:
            await self.repo.update_status(
                analysis_id=analysis_id,
                status=AnalysisStatus.failed,
                error_message=str(err),
            )
            await self._publish_event(
                analysis.organization_id,
                analysis_id,
                {"status": "failed", "error": str(err)},
            )
            raise

    async def _publish_event(self, org_id: uuid.UUID, analysis_id: uuid.UUID, data: Dict[str, Any]) -> None:
        try:
            r = aioredis.from_url(settings.REDIS_URL)
            channel = f"analyses:{analysis_id}"
            await r.publish(channel, json.dumps(data))
            await r.aclose()
        except Exception:
            pass  # Non-blocking if redis pub/sub not active
