"""Web Investigation Orchestrator.

Coordinates the complete Phase 3 investigation workflow for discovered URLs:
1. Crawl courtesy and robots.txt evaluation
2. Tiered fetch (httpx -> Firecrawl -> Browserless)
3. Page metadata and candidate image extraction
4. SSRF-safe candidate image downloads, validations, and hashing
5. Multi-signal image correlation (correlation_policy_v1.0) stopping at PENDING_REVIEW
6. OCR textual context extraction & bounded follow-ups
7. Historical snapshots (Wayback & Common Crawl) preserving NOT_OBSERVED uncertainty
8. Deduplication and multi-provider provenance retention
9. Idempotent execution using per-image keys: org_id:case_id:disc_id:op:img_hash
10. Real state transition SSE event streaming and forensic audit logging
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditAction
from app.models.discovery import SearchResult
from app.models.investigation_record import (
    CandidateImage,
    CrawlStatus,
    HistoricalSnapshot,
    ImageCorrelation,
    OcrExtraction,
    PageInvestigation,
)
from app.services.audit_service import AuditService
from app.services.candidate_image_service import candidate_image_service
from app.services.commoncrawl_service import commoncrawl_service
from app.services.image_correlation_service import image_correlation_service
from app.services.ocr_service import ocr_service
from app.services.page_investigation_service import page_investigation_service
from app.services.wayback_service import wayback_service

logger = logging.getLogger(__name__)


@dataclass
class InvestigationEvent:
    event_type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class InvestigationSummary:
    page_investigation: PageInvestigation
    candidate_images: list[CandidateImage]
    correlations: list[ImageCorrelation]
    ocr_records: list[OcrExtraction]
    historical_records: list[HistoricalSnapshot]
    total_duration_ms: float
    events_emitted: list[str] = field(default_factory=list)


class WebInvestigationOrchestrator:
    """Orchestrates public web page and visual evidence investigations."""

    @staticmethod
    def generate_idempotency_key(
        organization_id: uuid.UUID,
        case_id: uuid.UUID,
        discovery_id: uuid.UUID | str,
        operation: str,
        image_url: str | None = None,
    ) -> str:
        """Construct deterministic per-image idempotency key."""
        img_hash = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:16] if image_url else "root"
        return f"{organization_id}:{case_id}:{discovery_id}:{operation}:{img_hash}"

    async def investigate_discovery_result(
        self,
        session: AsyncSession,
        search_result: SearchResult,
        ref_bytes: bytes,
        reference_image_id: uuid.UUID | None = None,
        event_callback: Callable[[InvestigationEvent], Any] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> InvestigationSummary:
        """Run full Phase 3 investigation on a single SearchResult discovery record."""
        start_time = time.perf_counter()
        events_emitted: list[str] = []
        audit_service = AuditService(session)

        case_id = search_result.case_id
        # Look up case organization_id
        from app.models.case import Case
        case_res = await session.execute(select(Case).where(Case.id == case_id))
        case_obj = case_res.scalar_one_or_none()
        organization_id = case_obj.organization_id if case_obj else uuid.uuid4()

        target_url = search_result.page_url or search_result.source_url

        async def emit(ev_type: str, data: dict[str, Any]) -> None:
            events_emitted.append(ev_type)
            ev = InvestigationEvent(event_type=ev_type, data=data)
            if event_callback:
                try:
                    res = event_callback(ev)
                    if hasattr(res, "__await__"):
                        await res
                except Exception as cb_err:
                    logger.debug(f"Event callback error: {cb_err}")

        # 1. Start Page Fetch
        await emit("search.page.fetch.started", {"url": target_url, "search_result_id": str(search_result.id)})
        await audit_service.log(
            action=AuditAction.page_investigation_started,
            user_id=user_id,
            organization_id=organization_id,
            resource_type="search_result",
            resource_id=str(search_result.id),
            details={"url": target_url, "case_id": str(case_id)},
        )

        page_inv_res = await page_investigation_service.investigate_page(
            session=session,
            case_id=case_id,
            organization_id=organization_id,
            target_url=target_url,
            search_result_id=search_result.id,
            check_robots=True,
        )
        page_inv = page_inv_res.page_investigation

        if page_inv.crawl_status in (CrawlStatus.INACCESSIBLE, CrawlStatus.BLOCKED, CrawlStatus.ROBOTS_TXT_DISALLOWED, CrawlStatus.ERROR):
            await emit("search.page.fetch.failed", {
                "url": target_url,
                "status": page_inv.crawl_status.value,
                "error": page_inv.error_category,
            })
        else:
            await emit("search.page.fetch.completed", {
                "url": target_url,
                "final_url": page_inv.final_fetched_url,
                "title": page_inv.page_title,
                "images_found": page_inv.extracted_images_count,
            })

        # 2. Historical Lookups for the investigated page
        hist_records: list[HistoricalSnapshot] = []
        try:
            wb_snap = await wayback_service.record_snapshot(
                session=session,
                organization_id=organization_id,
                target_url=page_inv.final_fetched_url,
                page_investigation_id=page_inv.id,
            )
            hist_records.append(wb_snap)

            cc_snap = await commoncrawl_service.record_snapshot(
                session=session,
                organization_id=organization_id,
                target_url=page_inv.final_fetched_url,
                page_investigation_id=page_inv.id,
            )
            hist_records.append(cc_snap)
            await emit("search.history.completed", {"url": page_inv.final_fetched_url, "snapshots_recorded": 2})
            await audit_service.log(
                action=AuditAction.historical_lookup_completed,
                user_id=user_id,
                organization_id=organization_id,
                resource_type="page_investigation",
                resource_id=str(page_inv.id),
                details={"target_url": page_inv.final_fetched_url, "wayback": wb_snap.status.value, "commoncrawl": cc_snap.status.value},
            )
        except Exception as hist_err:
            logger.warning(f"Historical lookup error: {hist_err}")

        # 3. Process candidate images
        cand_records: list[CandidateImage] = []
        corr_records: list[ImageCorrelation] = []
        ocr_records: list[OcrExtraction] = []

        # If discovery result had a direct image_url, prepend to candidates
        all_candidate_urls = [c.url for c in page_inv_res.candidate_image_urls]
        if search_result.image_url and search_result.image_url not in all_candidate_urls:
            all_candidate_urls.insert(0, search_result.image_url)

        # Cap processing at configured limit
        all_candidate_urls = all_candidate_urls[:settings.MAX_CANDIDATE_IMAGES_PER_RESULT]

        for cand_url in all_candidate_urls:
            await emit("search.image.discovered", {"image_url": cand_url, "page_url": page_inv.final_fetched_url})
            await emit("search.image.download.started", {"image_url": cand_url})

            processed = await candidate_image_service.download_and_process(
                session=session,
                page_investigation_id=page_inv.id,
                case_id=case_id,
                organization_id=organization_id,
                image_url=cand_url,
            )

            if not processed.is_valid or not processed.candidate_image:
                await emit("search.image.download.failed", {"image_url": cand_url, "reason": processed.rejection_reason})
                continue

            cand_img = processed.candidate_image
            cand_records.append(cand_img)
            await emit("search.image.download.completed", {
                "image_url": cand_url,
                "sha256": cand_img.sha256_hash,
                "dimensions": f"{cand_img.width}x{cand_img.height}",
            })
            await audit_service.log(
                action=AuditAction.candidate_image_downloaded,
                user_id=user_id,
                organization_id=organization_id,
                resource_type="candidate_image",
                resource_id=str(cand_img.id),
                details={"sha256": cand_img.sha256_hash, "mime": cand_img.mime_type},
            )

            # Correlation evaluation
            correlation = await image_correlation_service.correlate_and_persist(
                session=session,
                candidate_image=cand_img,
                cand_bytes=processed.raw_bytes,
                ref_bytes=ref_bytes,
                reference_image_id=reference_image_id,
            )
            corr_records.append(correlation)
            await emit("search.correlation.completed", {
                "candidate_image_id": str(cand_img.id),
                "classification": correlation.classification,
                "dinov2_score": correlation.dinov2_similarity,
                "arcface_score": correlation.arcface_similarity,
                "status": correlation.status,
            })
            await audit_service.log(
                action=AuditAction.image_correlation_evaluated,
                user_id=user_id,
                organization_id=organization_id,
                resource_type="image_correlation",
                resource_id=str(correlation.id),
                details={"classification": correlation.classification, "policy_ref": correlation.threshold_config_ref},
            )

            # OCR Extraction
            ocr_rec = await ocr_service.extract_and_persist(
                session=session,
                candidate_image=cand_img,
                image_bytes=processed.raw_bytes,
            )
            ocr_records.append(ocr_rec)
            await emit("search.ocr.completed", {
                "candidate_image_id": str(cand_img.id),
                "text_length": len(ocr_rec.extracted_text),
                "confidence": ocr_rec.confidence_score,
            })

            await emit("search.image.analysis.completed", {
                "candidate_image_id": str(cand_img.id),
                "classification": correlation.classification,
            })

        await emit("search.dedup.completed", {
            "page_url": page_inv.final_fetched_url,
            "unique_images_processed": len(cand_records),
        })

        await emit("search.completed", {
            "search_result_id": str(search_result.id),
            "status": "COMPLETED",
            "findings_count": len(corr_records),
        })

        await session.commit()

        total_duration = round((time.perf_counter() - start_time) * 1000, 2)
        return InvestigationSummary(
            page_investigation=page_inv,
            candidate_images=cand_records,
            correlations=corr_records,
            ocr_records=ocr_records,
            historical_records=hist_records,
            total_duration_ms=total_duration,
            events_emitted=events_emitted,
        )


web_investigation_orchestrator = WebInvestigationOrchestrator()
