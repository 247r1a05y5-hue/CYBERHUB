"""Cases API endpoints — Complete 9-stage investigation lifecycle."""
from __future__ import annotations

import base64
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_case_for_user, get_current_user, get_db
from app.core.rate_limit import rate_limit
from app.models.case import Case, CaseStatus
from app.models.dataset import DatasetIdentity
from app.models.discovery import ConfidenceCategory, JobStatus, Match, SearchJob, SearchResult
from app.models.evidence import Evidence, VerificationStatus
from app.models.intelligence import Complaint, ComplaintStatus, MonitoringRule, Report, ReportFormat, RiskAssessment, TimelineEvent
from app.models.user import User
from app.schemas.case import (
    CaptureResponse,
    CaptureUploadRequest,
    CaseCreateRequest,
    CaseResponse,
    ComplaintDraftRequest,
    ComplaintResponse,
    ComplaintReviewRequest,
    EvidenceResponse,
    MatchConfirmRequest,
    MatchResponse,
    MonitoringRuleRequest,
    MonitoringRuleResponse,
    ReportGenerateRequest,
    ReportResponse,
    RiskAssessmentResponse,
    ScanJobResponse,
    SearchResultResponse,
    VerifyFindingRequest,
)
from app.services.audit_service import AuditService
from app.services.correlation_service import CorrelationEngine
from app.services.dataset_service import DatasetService
from app.services.discovery_service import DiscoveryService
from app.services.evidence_service import EvidenceService
from app.services.face_service import FaceValidationService
from app.services.matching_service import MatchingService
from app.services.monitoring_service import MonitoringService
from app.services.report_service import ReportService
from app.services.risk_service import RiskService

router = APIRouter()


# ── 1. Case CRUD ─────────────────────────────────────────────────────────────
@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED, summary="Create a new investigation case")
async def create_case(
    req: CaseCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit(max_requests=20, window_seconds=60)),
) -> CaseResponse:
    case_num = f"CH-{datetime_year()}-{str(uuid.uuid4())[:4].upper()}"
    case_obj = Case(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        case_number=case_num,
        title=req.title,
        description=req.description,
        target_subject_label=req.target_subject_label,
        status=CaseStatus.DRAFT,
        current_stage=1,
    )
    session.add(case_obj)
    await session.flush()

    # Timeline event
    t_evt = TimelineEvent(
        case_id=case_obj.id,
        event_type="CASE_CREATED",
        title="Investigation Created",
        description=f"Case {case_num} initialized by {current_user.email}",
        actor_id=current_user.id,
    )
    session.add(t_evt)
    await session.commit()
    await session.refresh(case_obj)

    return CaseResponse(
        id=case_obj.id,
        case_number=case_obj.case_number,
        title=case_obj.title,
        description=case_obj.description,
        target_subject_label=case_obj.target_subject_label,
        status=case_obj.status.value,
        current_stage=case_obj.current_stage,
        created_at=case_obj.created_at,
        updated_at=case_obj.updated_at,
    )


@router.get("", response_model=list[CaseResponse], summary="List all cases for the authenticated organization")
async def list_cases(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CaseResponse]:
    stmt = select(Case).where(Case.organization_id == current_user.organization_id).order_by(Case.created_at.desc())
    res = await session.execute(stmt)
    cases = res.scalars().all()
    return [
        CaseResponse(
            id=c.id,
            case_number=c.case_number,
            title=c.title,
            description=c.description,
            target_subject_label=c.target_subject_label,
            status=c.status.value,
            current_stage=c.current_stage,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in cases
    ]


@router.get("/{id}", response_model=CaseResponse, summary="Get case details by ID")
async def get_case(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
) -> CaseResponse:
    return CaseResponse(
        id=case_obj.id,
        case_number=case_obj.case_number,
        title=case_obj.title,
        description=case_obj.description,
        target_subject_label=case_obj.target_subject_label,
        status=case_obj.status.value,
        current_stage=case_obj.current_stage,
        created_at=case_obj.created_at,
        updated_at=case_obj.updated_at,
    )


# ── 2. Camera Capture & Face Validation ──────────────────────────────────────
@router.post("/{id}/capture", response_model=CaptureResponse, summary="Submit captured face photo for validation")
async def capture_photo(
    id: uuid.UUID,
    req: CaptureUploadRequest,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit(max_requests=15, window_seconds=60)),
) -> CaptureResponse:
    face_service = FaceValidationService(session)

    # Process payload
    if req.image_base64:
        raw_bytes = base64.b64decode(req.image_base64.split(",")[-1])
        img_url = f"/storage/cases/{case_obj.id}/captured.jpg"
    else:
        raw_bytes = b"MOCK_FACE_CAPTURE_BYTES_0x9B"
        img_url = req.image_url or "/assets/identities/captured_preview.jpg"

    ref_image, face_record = await face_service.process_capture(
        case_id=case_obj.id,
        image_bytes=raw_bytes,
        image_url=img_url,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )

    if face_record.is_valid:
        case_obj.status = CaseStatus.VALIDATED
        case_obj.current_stage = 2
        # Record timeline event
        session.add(
            TimelineEvent(
                case_id=case_obj.id,
                event_type="FACE_VALIDATED",
                title="Biometric Face Validated",
                description=f"Face quality score {face_record.quality_score:.2f} — verified 1 subject in frame",
                actor_id=current_user.id,
            )
        )

    await session.commit()

    return CaptureResponse(
        reference_image_id=ref_image.id,
        image_url=ref_image.image_url,
        sha256_hash=ref_image.sha256_hash,
        quality_score=face_record.quality_score,
        face_count=face_record.face_count,
        validation_status=face_record.validation_status.value,
        is_valid=face_record.is_valid,
    )


# ── 3. Bounded Identity Matching ─────────────────────────────────────────────
@router.post("/{id}/match", response_model=list[MatchResponse], summary="Run bounded identity matching against authorized dataset")
async def run_matching(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[MatchResponse]:
    dataset_service = DatasetService(session)
    matching_service = MatchingService(session)

    dataset = await dataset_service.get_or_create_default_dataset(current_user.organization_id)
    matches = await matching_service.search_dataset(case_obj, dataset.id, user_id=current_user.id)
    await session.commit()

    # Load candidate info
    res: list[MatchResponse] = []
    for m in matches:
        stmt_id = select(DatasetIdentity).where(DatasetIdentity.id == m.dataset_identity_id)
        ident = (await session.execute(stmt_id)).scalar_one_or_none()

        res.append(
            MatchResponse(
                id=m.id,
                case_id=m.case_id,
                dataset_identity_id=m.dataset_identity_id,
                candidate_name=ident.full_name if ident else "Unknown",
                candidate_code=ident.identity_code if ident else "N/A",
                photo_url=ident.photo_url if ident else None,
                similarity_score=m.similarity_score,
                confidence_category=m.confidence_category.value,
                is_confirmed=m.is_confirmed,
                review_notes=m.review_notes,
                signals=m.signals_json,
            )
        )
    return res


@router.post("/{id}/match/confirm", response_model=MatchResponse, summary="Confirm or reject candidate match")
async def confirm_match(
    id: uuid.UUID,
    req: MatchConfirmRequest,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MatchResponse:
    matching_service = MatchingService(session)
    match_obj = await matching_service.confirm_match(
        case=case_obj,
        match_id=req.match_id,
        confirmed=req.confirmed,
        user_id=current_user.id,
        review_notes=req.review_notes,
    )

    if req.confirmed:
        session.add(
            TimelineEvent(
                case_id=case_obj.id,
                event_type="IDENTITY_CONFIRMED",
                title="Identity Match Confirmed",
                description=f"Subject confirmed as {case_obj.target_subject_label} (Confidence: {match_obj.confidence_category.value})",
                actor_id=current_user.id,
            )
        )

    await session.commit()

    stmt_id = select(DatasetIdentity).where(DatasetIdentity.id == match_obj.dataset_identity_id)
    ident = (await session.execute(stmt_id)).scalar_one_or_none()

    return MatchResponse(
        id=match_obj.id,
        case_id=match_obj.case_id,
        dataset_identity_id=match_obj.dataset_identity_id,
        candidate_name=ident.full_name if ident else "Unknown",
        candidate_code=ident.identity_code if ident else "N/A",
        photo_url=ident.photo_url if ident else None,
        similarity_score=match_obj.similarity_score,
        confidence_category=match_obj.confidence_category.value,
        is_confirmed=match_obj.is_confirmed,
        review_notes=match_obj.review_notes,
        signals=match_obj.signals_json,
    )


# ── 4. Discovery Scan & SSE Stream ───────────────────────────────────────────
@router.post("/{id}/scan", response_model=ScanJobResponse, status_code=status.HTTP_202_ACCEPTED, summary="Initiate exposure discovery scan")
async def start_scan(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit(max_requests=10, window_seconds=60)),
) -> ScanJobResponse:
    discovery_service = DiscoveryService(session)
    job = await discovery_service.create_scan_job(case_obj, user_id=current_user.id)

    # In demo mode, run scan inline or via worker
    await discovery_service.execute_scan(job.id)

    session.add(
        TimelineEvent(
            case_id=case_obj.id,
            event_type="DISCOVERY_COMPLETED",
            title="Exposure Scan Completed",
            description=f"Discovery completed with {job.total_found} potential exposure findings",
            actor_id=current_user.id,
        )
    )
    await session.commit()
    await session.refresh(job)

    return ScanJobResponse(
        job_id=job.id,
        case_id=job.case_id,
        provider=job.provider,
        status=job.status.value,
        progress_pct=job.progress_pct,
        current_step=job.current_step,
        total_found=job.total_found,
    )


@router.get("/{id}/exposures", response_model=list[SearchResultResponse], summary="List discovered search results")
async def list_exposures(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
    session: AsyncSession = Depends(get_db),
) -> list[SearchResultResponse]:
    stmt = select(SearchResult).where(SearchResult.case_id == case_obj.id).order_by(SearchResult.similarity_score.desc())
    results = list((await session.execute(stmt)).scalars().all())
    return [
        SearchResultResponse(
            id=r.id,
            provider=r.provider,
            source_url=r.source_url,
            page_url=r.page_url,
            image_url=r.image_url,
            domain=r.domain,
            page_title=r.page_title,
            discovered_at=r.discovered_at,
            similarity_score=r.similarity_score,
            result_type=r.result_type,
            metadata=r.metadata_json,
        )
        for r in results
    ]


# ── 5. Correlation & Exposure Graph ──────────────────────────────────────────
@router.get("/{id}/graph", summary="Get Exposure Graph nodes and edges")
async def get_graph(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    correlation_engine = CorrelationEngine(session)
    await correlation_engine.correlate_case_findings(case_obj)
    graph_data = await correlation_engine.build_exposure_graph(case_obj)
    await session.commit()
    return {
        "nodes": graph_data.nodes,
        "edges": graph_data.edges,
        "total_nodes": graph_data.total_nodes,
        "total_edges": graph_data.total_edges,
        "cluster_count": graph_data.cluster_count,
    }


# ── 6. Verification & Evidence Vault ─────────────────────────────────────────
@router.post("/{id}/evidence/verify", response_model=EvidenceResponse, summary="Verify finding and store in Evidence Vault")
async def verify_finding(
    id: uuid.UUID,
    req: VerifyFindingRequest,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    evidence_service = EvidenceService(session)
    status_enum = VerificationStatus(req.status.upper())
    evidence = await evidence_service.verify_finding(
        case=case_obj,
        result_id=req.result_id,
        status=status_enum,
        user_reason=req.user_reason,
        user_id=current_user.id,
    )

    session.add(
        TimelineEvent(
            case_id=case_obj.id,
            event_type="EVIDENCE_PRESERVED",
            title=f"Evidence {evidence.evidence_number} Preserved",
            description=f"Status: {status_enum.value} on domain {evidence.domain} (SHA-256: {evidence.sha256_hash[:12]}...)",
            actor_id=current_user.id,
        )
    )
    await session.commit()

    return EvidenceResponse(
        id=evidence.id,
        evidence_number=evidence.evidence_number,
        source_url=evidence.source_url,
        page_url=evidence.page_url,
        image_url=evidence.image_url,
        domain=evidence.domain,
        page_title=evidence.page_title,
        screenshot_path=evidence.screenshot_path,
        sha256_hash=evidence.sha256_hash,
        verification_status=evidence.verification_status.value,
        user_reason=evidence.user_reason,
        chain_of_custody=evidence.chain_of_custody_json,
    )


@router.get("/{id}/evidence", response_model=list[EvidenceResponse], summary="List evidence items in case vault")
async def list_evidence(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
    session: AsyncSession = Depends(get_db),
) -> list[EvidenceResponse]:
    stmt = select(Evidence).where(Evidence.case_id == case_obj.id).order_by(Evidence.created_at.desc())
    items = list((await session.execute(stmt)).scalars().all())
    return [
        EvidenceResponse(
            id=e.id,
            evidence_number=e.evidence_number,
            source_url=e.source_url,
            page_url=e.page_url,
            image_url=e.image_url,
            domain=e.domain,
            page_title=e.page_title,
            screenshot_path=e.screenshot_path,
            sha256_hash=e.sha256_hash,
            verification_status=e.verification_status.value,
            user_reason=e.user_reason,
            chain_of_custody=e.chain_of_custody_json,
        )
        for e in items
    ]


# ── 7. Risk Engine ───────────────────────────────────────────────────────────
@router.post("/{id}/risk", response_model=RiskAssessmentResponse, summary="Compute deterministic risk assessment")
async def assess_risk(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RiskAssessmentResponse:
    risk_service = RiskService(session)
    assessment = await risk_service.compute_case_risk(case_obj, user_id=current_user.id)

    session.add(
        TimelineEvent(
            case_id=case_obj.id,
            event_type="RISK_ASSESSED",
            title=f"Risk Calculated: {assessment.overall_risk_level.value}",
            description=f"Calculated Score {assessment.calculated_score}/100 — {assessment.explanation_text}",
            actor_id=current_user.id,
        )
    )
    await session.commit()

    return RiskAssessmentResponse(
        id=assessment.id,
        overall_risk_level=assessment.overall_risk_level.value,
        calculated_score=assessment.calculated_score,
        explanation_text=assessment.explanation_text,
        factor_breakdown=assessment.factor_breakdown_json,
    )


@router.get("/{id}/risk", response_model=RiskAssessmentResponse | None, summary="Get latest risk assessment")
async def get_risk(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
    session: AsyncSession = Depends(get_db),
) -> RiskAssessmentResponse | None:
    stmt = select(RiskAssessment).where(RiskAssessment.case_id == case_obj.id).order_by(RiskAssessment.created_at.desc())
    assessment = (await session.execute(stmt)).scalars().first()
    if not assessment:
        return None
    return RiskAssessmentResponse(
        id=assessment.id,
        overall_risk_level=assessment.overall_risk_level.value,
        calculated_score=assessment.calculated_score,
        explanation_text=assessment.explanation_text,
        factor_breakdown=assessment.factor_breakdown_json,
    )


# ── 8. Timeline & Reports ────────────────────────────────────────────────────
@router.get("/{id}/timeline", summary="Get case timeline events")
async def get_timeline(
    id: uuid.UUID,
    case_obj: Case = Depends(get_case_for_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    stmt = select(TimelineEvent).where(TimelineEvent.case_id == case_obj.id).order_by(TimelineEvent.created_at.asc())
    events = list((await session.execute(stmt)).scalars().all())
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "title": e.title,
            "description": e.description,
            "timestamp": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.post("/{id}/report", response_model=ReportResponse, summary="Generate exportable case report")
async def generate_report(
    id: uuid.UUID,
    req: ReportGenerateRequest,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReportResponse:
    report_service = ReportService(session)
    fmt = ReportFormat(req.format.upper())
    report = await report_service.generate_case_report(case_obj, fmt=fmt, user_id=current_user.id)

    session.add(
        TimelineEvent(
            case_id=case_obj.id,
            event_type="REPORT_GENERATED",
            title=f"Report Generated ({fmt.value})",
            description=f"Export bundle compiled with SHA-256 seal: {report.sha256_hash[:12]}...",
            actor_id=current_user.id,
        )
    )
    await session.commit()

    return ReportResponse(
        id=report.id,
        report_title=report.report_title,
        report_format=report.report_format.value,
        file_path=report.file_path,
        sha256_hash=report.sha256_hash,
        generated_at=report.created_at,
        summary=report.summary_json,
    )


# ── 9. Complaint Package ─────────────────────────────────────────────────────
@router.post("/{id}/complaint/draft", response_model=ComplaintResponse, summary="Generate legal/takedown complaint draft")
async def create_complaint(
    id: uuid.UUID,
    req: ComplaintDraftRequest,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComplaintResponse:
    report_service = ReportService(session)
    complaint = await report_service.create_complaint_draft(case_obj, target_entity=req.target_entity, user_id=current_user.id)
    await session.commit()

    return ComplaintResponse(
        id=complaint.id,
        target_entity=complaint.target_entity,
        incident_summary=complaint.incident_summary,
        draft_body=complaint.draft_body,
        status=complaint.status.value,
    )


@router.post("/{id}/complaint/{complaint_id}/review", response_model=ComplaintResponse, summary="Review and approve complaint draft")
async def review_complaint(
    id: uuid.UUID,
    complaint_id: uuid.UUID,
    req: ComplaintReviewRequest,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComplaintResponse:
    report_service = ReportService(session)
    status_enum = ComplaintStatus(req.status.upper())
    complaint = await report_service.review_complaint_draft(complaint_id, status_enum, user_id=current_user.id)
    await session.commit()

    return ComplaintResponse(
        id=complaint.id,
        target_entity=complaint.target_entity,
        incident_summary=complaint.incident_summary,
        draft_body=complaint.draft_body,
        status=complaint.status.value,
    )


# ── 10. Monitoring ───────────────────────────────────────────────────────────
@router.post("/{id}/monitoring", response_model=MonitoringRuleResponse, summary="Configure case monitoring rule")
async def configure_monitoring(
    id: uuid.UUID,
    req: MonitoringRuleRequest,
    case_obj: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MonitoringRuleResponse:
    monitoring_service = MonitoringService(session)
    rule = await monitoring_service.create_or_update_rule(
        case=case_obj,
        frequency=req.frequency,
        enabled=req.enabled,
        user_id=current_user.id,
    )

    session.add(
        TimelineEvent(
            case_id=case_obj.id,
            event_type="MONITORING_ACTIVE",
            title="Continuous Monitoring Activated",
            description=f"Frequency: {req.frequency} · Watching for new exposure occurrences",
            actor_id=current_user.id,
        )
    )
    await session.commit()

    return MonitoringRuleResponse(
        id=rule.id,
        frequency=rule.frequency,
        enabled=rule.enabled,
        previous_count=rule.previous_count,
        current_count=rule.current_count,
        new_delta_count=rule.new_delta_count,
        last_run_at=rule.last_run_at,
    )


def datetime_year() -> str:
    import datetime
    return str(datetime.datetime.now().year)
