"""Monitoring Service — Case-scoped exposure monitoring, delta diff calculation & re-scan orchestration."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.audit_log import AuditAction
from app.models.biometrics import ReferenceImage
from app.models.case import Case, CaseStatus
from app.models.discovery import JobStatus, SearchJob, SearchResult
from app.models.intelligence import MonitoringRule, MonitoringRun
from app.services.audit_service import AuditService
from app.services.exposure_scan_orchestrator import ScanProgressEvent, exposure_scan_orchestrator
from app.services.image_matching_service import image_matching_service
from app.services.provider_orchestration_service import provider_orchestrator
from app.services.timeline_service import timeline_service

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service to manage periodic re-scans strictly scoped to the owning case and tenant."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_service = AuditService(session)

    async def get_rule_for_case(self, case_id: uuid.UUID, org_id: uuid.UUID) -> MonitoringRule | None:
        """Get monitoring rule strictly verifying tenant ownership."""
        stmt = (
            select(MonitoringRule)
            .join(Case, Case.id == MonitoringRule.case_id)
            .where(MonitoringRule.case_id == case_id, Case.organization_id == org_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_history_for_case(
        self,
        case_id: uuid.UUID,
        org_id: uuid.UUID,
        limit: int = 20,
    ) -> list[MonitoringRun]:
        """Fetch historical monitoring runs for a case."""
        stmt = (
            select(MonitoringRun)
            .where(
                MonitoringRun.case_id == case_id,
                MonitoringRun.organization_id == org_id,
            )
            .order_by(desc(MonitoringRun.started_at))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_or_update_rule(
        self,
        case: Case,
        frequency: str = "DAILY",
        enabled: bool = True,
        user_id: uuid.UUID | None = None,
    ) -> MonitoringRule:
        """Create or configure a case-scoped monitoring rule."""
        stmt = select(MonitoringRule).where(MonitoringRule.case_id == case.id)
        rule = (await self.session.execute(stmt)).scalar_one_or_none()

        stmt_count = select(SearchResult).where(SearchResult.case_id == case.id)
        current_res = list((await self.session.execute(stmt_count)).scalars().all())
        current_count = len(current_res)

        interval_hours = 24 if frequency.upper() == "DAILY" else 168
        next_run = datetime.now(timezone.utc) + timedelta(hours=interval_hours)

        if not rule:
            rule = MonitoringRule(
                case_id=case.id,
                rule_name=f"Automated Exposure Watch — {case.case_number}",
                provider="GoogleCloudVision,TinEye",
                frequency=frequency.upper(),
                enabled=enabled,
                last_status="ACTIVE" if enabled else "PAUSED",
                previous_count=current_count,
                current_count=current_count,
                new_delta_count=0,
                last_run_at=datetime.now(timezone.utc),
                next_run_at=next_run if enabled else None,
            )
            self.session.add(rule)
        else:
            rule.frequency = frequency.upper()
            rule.enabled = enabled
            rule.last_status = "ACTIVE" if enabled else "PAUSED"
            if enabled and not rule.next_run_at:
                rule.next_run_at = next_run
            elif not enabled:
                rule.next_run_at = None

        if enabled:
            case.status = CaseStatus.MONITORING_ACTIVE
            case.current_stage = 9

        # Record timeline event
        await timeline_service.record_event(
            db=self.session,
            case_id=case.id,
            event_type="MONITORING_ENABLED" if enabled else "MONITORING_PAUSED",
            title=f"Monitoring {'Activated' if enabled else 'Paused'}",
            description=f"Continuous exposure monitoring is {rule.last_status.lower()} on cadence: {rule.frequency}.",
            actor_id=user_id,
            metadata={"rule_id": str(rule.id), "frequency": rule.frequency, "enabled": enabled},
        )

        # Emit SSE
        await exposure_scan_orchestrator.broadcast_event(
            ScanProgressEvent(
                event_type="monitoring.started" if enabled else "monitoring.paused",
                investigation_id=str(case.id),
                job_id=str(rule.id),
                step="MONITORING_CONFIGURED",
                progress_pct=100,
                message=f"Investigation monitoring is {rule.last_status.lower()} ({rule.frequency}).",
                timestamp=datetime.now(timezone.utc).isoformat(),
                payload={"rule_id": str(rule.id), "enabled": enabled, "frequency": rule.frequency},
            )
        )

        await self.session.flush()

        await self.audit_service.log(
            action=AuditAction.monitoring_updated,
            user_id=user_id,
            organization_id=case.organization_id,
            resource_type="monitoring_rule",
            resource_id=str(rule.id),
            details={"enabled": enabled, "frequency": frequency, "case_id": str(case.id)},
        )

        return rule

    async def execute_monitoring_scan(
        self,
        rule_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        candidate_source_override: list[dict[str, Any]] | None = None,
    ) -> MonitoringRun:
        """
        Execute scheduled or manual re-scan strictly scoped to owning case & tenant.
        Applies rigorous delta comparison: NEW, UNCHANGED, NOT_OBSERVED_IN_LATEST_SCAN, REAPPEARED.
        """
        stmt = (
            select(MonitoringRule)
            .join(Case, Case.id == MonitoringRule.case_id)
            .where(MonitoringRule.id == rule_id)
        )
        rule = (await self.session.execute(stmt)).scalar_one_or_none()
        if not rule:
            raise ValueError(f"MonitoringRule {rule_id} not found")

        case_stmt = select(Case).where(Case.id == rule.case_id)
        case = (await self.session.execute(case_stmt)).scalar_one()

        started_at = datetime.now(timezone.utc)

        # Broadcast SSE: monitoring.scan.started
        await exposure_scan_orchestrator.broadcast_event(
            ScanProgressEvent(
                event_type="monitoring.scan.started",
                investigation_id=str(case.id),
                job_id=str(rule.id),
                step="MONITORING_SCAN_STARTED",
                progress_pct=10,
                message="Scheduled monitoring scan initiated across registered providers...",
                timestamp=started_at.isoformat(),
            )
        )

        # Timeline event
        await timeline_service.record_event(
            db=self.session,
            case_id=case.id,
            event_type="MONITORING_SCAN_STARTED",
            title="Monitoring Re-Scan Dispatched",
            description=f"Automated monitoring scan checking for new or altered exposure endpoints. Frequency: {rule.frequency}",
            actor_id=user_id,
            metadata={"rule_id": str(rule.id)},
        )

        # 1. Fetch Reference Image
        ref_stmt = select(ReferenceImage).where(ReferenceImage.case_id == case.id)
        ref_images = (await self.session.execute(ref_stmt)).scalars().all()
        ref = next((r for r in ref_images if r.is_primary), None) or (ref_images[0] if ref_images else None)
        ref_fingerprint = ref.sha256_hash if ref else "UNKNOWN"

        # 2. Fetch existing findings for delta comparison
        existing_stmt = select(SearchResult).where(SearchResult.case_id == case.id)
        existing_findings = list((await self.session.execute(existing_stmt)).scalars().all())
        existing_by_key: dict[str, SearchResult] = {}
        for f in existing_findings:
            key = f.metadata_json.get("canonical_url") or f.page_url or f.source_url or str(f.id)
            existing_by_key[key] = f

        # 3. Obtain current scan sources
        provider_statuses = provider_orchestrator.get_provider_statuses()
        active_provider_count = sum(1 for p in provider_statuses.values() if p["configured"])
        provider_summary_status = "READY" if active_provider_count > 0 else "NOT_CONFIGURED"

        discovered_items: list[dict[str, Any]] = []
        if candidate_source_override is not None:
            discovered_items = candidate_source_override
        elif active_provider_count == 0:
            # Honest status: No live providers configured, return 0 discoveries in production
            discovered_items = []
        else:
            # Query active providers
            provider_results = await provider_orchestrator.query_all(image_bytes=b"")
            for res in provider_results:
                discovered_items.append({
                    "url": res.url,
                    "page_url": res.page_url,
                    "domain": res.domain,
                    "page_title": res.page_title,
                    "similarity_score": res.similarity_score,
                    "provider": res.provider,
                })

        new_count = 0
        unchanged_count = 0
        not_observed_count = 0
        reappeared_count = 0
        verified_new_count = 0

        observed_keys: set[str] = set()

        # Create a SearchJob record for this monitoring run
        monitoring_job = SearchJob(
            case_id=case.id,
            provider=rule.provider or "MonitoringEngine",
            status=JobStatus.COMPLETED,
            progress_pct=100,
            current_step="MONITORING_SCAN_COMPLETED",
        )
        self.session.add(monitoring_job)
        await self.session.flush()

        # 4. Compare Discovered against Existing
        for item in discovered_items:
            item_url = item.get("page_url") or item.get("url") or item.get("source_url") or ""
            domain = item.get("domain") or "unknown.test"
            key = item_url or domain
            observed_keys.add(key)

            if key in existing_by_key:
                existing_item = existing_by_key[key]
                prev_obs_state = existing_item.metadata_json.get("observation_state", "ACTIVE")
                if prev_obs_state == "NOT_OBSERVED_IN_LATEST_SCAN":
                    existing_item.metadata_json["observation_state"] = "REAPPEARED"
                    existing_item.metadata_json["last_observed_at"] = datetime.now(timezone.utc).isoformat()
                    flag_modified(existing_item, "metadata_json")
                    reappeared_count += 1
                    # Broadcast SSE
                    await exposure_scan_orchestrator.broadcast_event(
                        ScanProgressEvent(
                            event_type="monitoring.reappeared",
                            investigation_id=str(case.id),
                            job_id=str(existing_item.id),
                            step="EXPOSURE_REAPPEARED",
                            progress_pct=50,
                            message=f"Exposure on {domain} reappeared in latest scan.",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            payload={"domain": domain, "url": item_url},
                        )
                    )
                else:
                    existing_item.metadata_json["observation_state"] = "UNCHANGED"
                    existing_item.metadata_json["last_observed_at"] = datetime.now(timezone.utc).isoformat()
                    flag_modified(existing_item, "metadata_json")
                    unchanged_count += 1
            else:
                # NEW candidate finding discovered
                new_finding = SearchResult(
                    case_id=case.id,
                    search_job_id=monitoring_job.id,
                    provider=item.get("provider", "MonitoringEngine"),
                    source_url=item_url,
                    page_url=item_url,
                    image_url=item.get("image_url", item_url),
                    domain=domain,
                    page_title=item.get("page_title", f"Discovered Source ({domain})"),
                    similarity_score=float(item.get("similarity_score", 0.85)),
                    result_type="CANDIDATE_DISCOVERED",
                    metadata_json={
                        "canonical_url": key,
                        "observation_state": "NEW",
                        "verification_status": "PENDING_REVIEW",
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                        "monitoring_run": True,
                    },
                )
                self.session.add(new_finding)
                new_count += 1

                # Broadcast SSE: monitoring.new_candidate (Clearly separated from confirmed exposure!)
                await exposure_scan_orchestrator.broadcast_event(
                    ScanProgressEvent(
                        event_type="monitoring.new_candidate",
                        investigation_id=str(case.id),
                        job_id=str(uuid.uuid4()),
                        step="NEW_CANDIDATE_DISCOVERED",
                        progress_pct=60,
                        message=f"New candidate finding discovered on {domain} — analyst review required.",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        payload={"domain": domain, "url": item_url, "status": "PENDING_REVIEW"},
                    )
                )

        # 5. Check for Existing findings that were NOT observed in this scan
        for key, existing_item in existing_by_key.items():
            if key not in observed_keys:
                existing_item.metadata_json["observation_state"] = "NOT_OBSERVED_IN_LATEST_SCAN"
                flag_modified(existing_item, "metadata_json")
                not_observed_count += 1
                await exposure_scan_orchestrator.broadcast_event(
                    ScanProgressEvent(
                        event_type="monitoring.not_observed",
                        investigation_id=str(case.id),
                        job_id=str(existing_item.id),
                        step="EXPOSURE_NOT_OBSERVED",
                        progress_pct=80,
                        message=f"Finding on {existing_item.domain} was not observed in latest scan (historical record preserved).",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        payload={"domain": existing_item.domain, "id": str(existing_item.id)},
                    )
                )

        completed_at = datetime.now(timezone.utc)
        total_active = len(existing_findings) + new_count

        # 6. Record MonitoringRun audit entry
        run = MonitoringRun(
            rule_id=rule.id,
            case_id=case.id,
            organization_id=case.organization_id,
            status="COMPLETED",
            provider_status=provider_summary_status,
            started_at=started_at,
            completed_at=completed_at,
            candidate_count=len(discovered_items),
            new_count=new_count,
            unchanged_count=unchanged_count,
            not_observed_count=not_observed_count,
            reappeared_count=reappeared_count,
            verified_new_count=verified_new_count,
            error_summary=None,
            details_json={
                "provider_statuses": provider_statuses,
                "observed_count": len(observed_keys),
                "total_historical_findings": total_active,
            },
        )
        self.session.add(run)

        # Update Rule statistics
        interval_hours = 24 if rule.frequency.upper() == "DAILY" else 168
        rule.previous_count = rule.current_count
        rule.current_count = total_active
        rule.new_delta_count = new_count
        rule.last_run_at = completed_at
        rule.next_run_at = completed_at + timedelta(hours=interval_hours)
        rule.last_status = "COMPLETED"

        # Append timeline event
        await timeline_service.record_event(
            db=self.session,
            case_id=case.id,
            event_type="MONITORING_SCAN_COMPLETED",
            title=f"Monitoring Re-Scan Complete (+{new_count} new candidates)",
            description=(
                f"Scan finished. Discovered {new_count} new candidate(s), {unchanged_count} unchanged, "
                f"{not_observed_count} unobserved, {reappeared_count} reappeared."
            ),
            actor_id=user_id,
            metadata={
                "run_id": str(run.id),
                "new_count": new_count,
                "unchanged_count": unchanged_count,
                "not_observed_count": not_observed_count,
                "reappeared_count": reappeared_count,
            },
        )

        # Broadcast SSE: monitoring.scan.completed
        await exposure_scan_orchestrator.broadcast_event(
            ScanProgressEvent(
                event_type="monitoring.scan.completed",
                investigation_id=str(case.id),
                job_id=str(run.id),
                step="MONITORING_SCAN_COMPLETED",
                progress_pct=100,
                message=f"Monitoring scan completed. {new_count} new candidate(s) discovered.",
                timestamp=completed_at.isoformat(),
                payload={
                    "run_id": str(run.id),
                    "new_count": new_count,
                    "unchanged_count": unchanged_count,
                    "not_observed_count": not_observed_count,
                    "reappeared_count": reappeared_count,
                },
            )
        )

        await self.session.commit()
        return run

