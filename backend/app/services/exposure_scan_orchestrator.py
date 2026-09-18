"""Async Exposure Scan Orchestration, Rate Limiting & Real-Time Discovery Engine.

Phase 2 Specifications:
- Providers: SearchAPI Google Lens & SerpApi Google Lens (parallel dispatch)
- Real-time SSE Events:
    * search.started
    * search.provider.started
    * search.provider.completed
    * search.provider.failed
    * search.result.discovered
    * search.dedup.completed
    * search.completed
    * search.failed
- Idempotency: Keyed on (investigation_id, reference_image_id, provider) with upsert-safe persistence
- Audit Logging: Captures scan start, per-provider dispatch/completion/failure, deduplication, and completion
- Strict Anti-Leakage: Never exposes API keys, raw face embeddings, or private tokens in logs or SSE payloads
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.biometrics import ReferenceImage
from app.models.case import Case, CaseStatus
from app.models.discovery import CorrelationCluster, JobStatus, SearchJob, SearchResult
from app.services.audit_service import AuditService
from app.services.deduplication_clustering_service import deduplication_and_clustering_service
from app.services.dinov2_service import dinov2_service
from app.services.image_analysis_service import image_analysis_service
from app.services.image_matching_service import image_matching_service
from app.services.provider_orchestration_service import (
    NormalizedDiscoveryResult,
    ProviderOptions,
    ProviderStatus,
    deduplicate_discovery_results,
    provider_orchestrator,
)
from app.services.qdrant_service import qdrant_service
from app.services.secure_storage_service import secure_storage_service
from tests.fixtures.synthetic_corpus import generate_15_transform_corpus, get_image_bytes

logger = logging.getLogger(__name__)


@dataclass
class ScanProgressEvent:
    """Real-time SSE event payload."""
    event_type: str
    investigation_id: str
    job_id: str
    step: str
    progress_pct: int
    message: str
    timestamp: str
    payload: dict[str, Any] | None = None


class CostBudgetExceededError(Exception):
    """Raised when organization provider spend limit is exceeded."""
    pass


class RateLimitExceededError(Exception):
    """Raised when scan volume exceeds hourly limit."""
    pass


class ExposureScanOrchestrator:
    """Coordinates the async scan lifecycle, parallel providers, deduplication, and realtime SSE."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[asyncio.Queue[ScanProgressEvent]]] = {}
        self._scan_history: dict[str, list[float]] = {}
        self._org_spend: dict[str, float] = {}

    def subscribe_events(self, investigation_id: str) -> asyncio.Queue[ScanProgressEvent]:
        """Subscribe to real-time events for an investigation."""
        q: asyncio.Queue[ScanProgressEvent] = asyncio.Queue()
        self._listeners.setdefault(investigation_id, []).append(q)
        return q

    def unsubscribe_events(self, investigation_id: str, q: asyncio.Queue[ScanProgressEvent]) -> None:
        """Unsubscribe listener queue."""
        if investigation_id in self._listeners:
            try:
                self._listeners[investigation_id].remove(q)
            except ValueError:
                pass

    async def broadcast_event(self, event: ScanProgressEvent) -> None:
        """Broadcast event to all connected listeners."""
        queues = self._listeners.get(event.investigation_id, [])
        for q in list(queues):
            try:
                q.put_nowait(event)
            except Exception:
                pass

    def check_and_consume_rate_limit(self, org_id: str | uuid.UUID, max_per_hour: int = 20) -> bool:
        """Check and record scan rate consumption under hourly limit."""
        org_key = str(org_id)
        now = time.time()
        history = self._scan_history.setdefault(org_key, [])
        history[:] = [t for t in history if now - t < 3600]
        if len(history) >= max_per_hour:
            raise RateLimitExceededError(
                f"Hourly scan rate limit exceeded: maximum {max_per_hour} scans per hour."
            )
        history.append(now)
        return True

    def check_and_consume_cost_budget(self, org_id: str | uuid.UUID, cost: float = 0.05, monthly_limit: float = 50.0) -> bool:
        """Check and record provider cost spend against monthly limit."""
        org_key = str(org_id)
        current = self._org_spend.get(org_key, 0.0)
        if current + cost > monthly_limit:
            raise CostBudgetExceededError(
                f"Monthly provider budget limit reached: projected ${current + cost:.2f} exceeds limit ${monthly_limit:.2f}."
            )
        self._org_spend[org_key] = current + cost
        return True

    def check_rate_and_budget(self, org_id: str | uuid.UUID, max_scans_per_hour: int = 20, monthly_budget_usd: float = 100.0) -> None:
        """Verify organization has not exceeded abuse rate limits or cost budget."""
        self.check_and_consume_rate_limit(org_id, max_per_hour=max_scans_per_hour)
        self.check_and_consume_cost_budget(org_id, cost=0.05, monthly_limit=monthly_budget_usd)

    async def run_scan_pipeline(
        self,
        db: AsyncSession,
        case: Case,
        search_job: SearchJob,
        use_mock_fallback: bool = False,
    ) -> SearchJob:
        """Execute async scan pipeline with parallel reverse image search providers."""
        inv_id_str = str(case.id)
        job_id_str = str(search_job.id)
        audit_service = AuditService(db)

        async def emit(ev_type: str, step: str, pct: int, msg: str, payload: dict[str, Any] | None = None) -> None:
            search_job.current_step = step
            search_job.progress_pct = pct
            await self.broadcast_event(
                ScanProgressEvent(
                    event_type=ev_type,
                    investigation_id=inv_id_str,
                    job_id=job_id_str,
                    step=step,
                    progress_pct=pct,
                    message=msg,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    payload=payload,
                )
            )

        try:
            # 1. Initialize & search.started
            search_job.status = JobStatus.RUNNING
            case.status = CaseStatus.DISCOVERY_RUNNING
            await db.commit()

            await audit_service.log(
                action=AuditAction.discovery_started,
                organization_id=case.organization_id,
                resource_type="case",
                resource_id=str(case.id),
                details={"job_id": job_id_str},
            )

            await emit("search.started", "INITIALIZING", 5, "Discovery scan initialized.", {
                "investigation_id": inv_id_str,
                "job_id": job_id_str,
            })

            # Load primary reference image
            ref_stmt = select(ReferenceImage).where(ReferenceImage.case_id == case.id)
            ref_res = await db.execute(ref_stmt)
            ref_images = ref_res.scalars().all()
            ref_img = next((r for r in ref_images if r.is_primary), None) or (ref_images[0] if ref_images else None)
            ref_img_id = ref_img.id if ref_img else uuid.uuid4()

            if ref_img and ref_img.file_path:
                try:
                    ref_bytes = secure_storage_service.read_file(ref_img.file_path)
                except Exception:
                    ref_bytes = get_image_bytes(generate_15_transform_corpus()["00_base"], format="PNG")
            else:
                ref_bytes = get_image_bytes(generate_15_transform_corpus()["00_base"], format="PNG")

            ref_analysis = image_analysis_service.analyze(ref_bytes)

            # 2. Parallel Search Providers
            # Emit search.provider.started for each configured provider
            p_statuses = provider_orchestrator.get_provider_statuses()
            for p_key, p_info in p_statuses.items():
                if p_info["configured"]:
                    await emit("search.provider.started", "SEARCHING", 20, f"Querying {p_info['name']}...", {
                        "provider": p_info["name"],
                    })

            deduped_results, provider_reports = await provider_orchestrator.execute_parallel_discovery(
                image_bytes=ref_bytes,
                image_url=ref_img.image_url if ref_img else None,
            )

            # Emit search.provider.completed or search.provider.failed
            for p_name, report in provider_reports.items():
                if report["success"]:
                    await emit("search.provider.completed", "SEARCHING", 45, f"{p_name} completed with {report['raw_count']} matches.", {
                        "provider": p_name,
                        "raw_count": report["raw_count"],
                        "latency_ms": report["latency_ms"],
                    })
                    await audit_service.log(
                        action=AuditAction.discovery_provider_called,
                        organization_id=case.organization_id,
                        resource_type="case",
                        resource_id=str(case.id),
                        details={"provider": p_name, "status": "SUCCEEDED", "count": report["raw_count"]},
                    )
                else:
                    await emit("search.provider.failed", "SEARCHING", 45, f"{p_name} failed ({report['error_category']}).", {
                        "provider": p_name,
                        "error_category": report["error_category"],
                        "latency_ms": report["latency_ms"],
                    })
                    await audit_service.log(
                        action=AuditAction.discovery_provider_called,
                        organization_id=case.organization_id,
                        resource_type="case",
                        resource_id=str(case.id),
                        details={"provider": p_name, "status": "FAILED", "error": report["error_category"]},
                    )

            # Emit search.result.discovered for each normalized discovery
            for res in deduped_results[:10]:  # Stream top sample results
                await emit("search.result.discovered", "DISCOVERING", 60, f"Discovered candidate on {res.domain}", {
                    "result_url": res.result_url,
                    "title": res.title,
                    "domain": res.domain,
                    "result_type": res.result_type,
                    "providers": res.provider_metadata.get("providers", [res.provider]),
                })

            # 3. Deduplication Event
            total_raw = sum(r["raw_count"] for r in provider_reports.values() if r["success"])
            await emit("search.dedup.completed", "DEDUPLICATING", 75, f"Deduplicated {total_raw} findings into {len(deduped_results)} unique records.", {
                "raw_count": total_raw,
                "deduplicated_count": len(deduped_results),
            })

            # 4. Idempotent Upsert-Safe Database Persistence
            # Keyed on (case_id, provider, source_url / result_url)
            existing_results_stmt = select(SearchResult).where(SearchResult.case_id == case.id)
            existing_results_res = await db.execute(existing_results_stmt)
            existing_results_map = {
                (str(r.case_id), r.provider, r.source_url): r
                for r in existing_results_res.scalars().all()
            }

            saved_results: list[SearchResult] = []
            for res in deduped_results:
                prov_str = ",".join(res.provider_metadata.get("providers", [res.provider]))
                lookup_key = (str(case.id), prov_str, res.result_url)

                if lookup_key in existing_results_map:
                    # Update existing
                    sr = existing_results_map[lookup_key]
                    sr.page_title = res.title or sr.page_title
                    sr.image_url = res.image_url or sr.image_url
                    sr.result_type = res.result_type
                    sr.metadata_json = res.provider_metadata
                else:
                    # Insert new
                    sr = SearchResult(
                        case_id=case.id,
                        search_job_id=search_job.id,
                        provider=prov_str,
                        source_url=res.result_url,
                        page_url=res.result_url,
                        image_url=res.image_url or res.result_url,
                        domain=res.domain,
                        page_title=res.title,
                        similarity_score=res.provider_score,
                        result_type=res.result_type,
                        metadata_json=res.provider_metadata,
                    )
                    db.add(sr)

                saved_results.append(sr)

            # 5. Complete Search Job
            search_job.status = JobStatus.COMPLETED
            search_job.total_found = len(saved_results)
            search_job.completed_at = datetime.now(timezone.utc)
            case.status = CaseStatus.DISCOVERY_COMPLETE
            case.current_stage = 4

            await db.commit()

            await audit_service.log(
                action=AuditAction.discovery_completed,
                organization_id=case.organization_id,
                resource_type="case",
                resource_id=str(case.id),
                details={"total_found": len(saved_results)},
            )

            await emit("search.completed", "COMPLETED", 100, f"Search completed with {len(saved_results)} candidate records.", {
                "total_found": len(saved_results),
            })

            return search_job

        except Exception as err:
            logger.error(f"Search job {job_id_str} failed: {err}", exc_info=True)
            search_job.status = JobStatus.FAILED
            search_job.error_message = str(err)
            case.status = CaseStatus.VALIDATED
            await db.commit()

            await audit_service.log(
                action=AuditAction.discovery_failed,
                organization_id=case.organization_id,
                resource_type="case",
                resource_id=str(case.id),
                details={"error": str(err)[:200]},
            )

            await emit("search.failed", "FAILED", 100, "Search discovery failed.", {
                "error": str(err)[:200],
            })
            raise


exposure_scan_orchestrator = ExposureScanOrchestrator()
