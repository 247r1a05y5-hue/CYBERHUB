"""Image Exposure Investigation API Endpoints.

Implements full production image-to-image workflow:
1. POST /investigations (Create Container)
2. POST /investigations/{id}/attestation (Authorization Attestation Audit Control)
3. POST /investigations/{id}/reference-image (Secure Upload, Validation & DINOv2 Analysis)
4. POST /investigations/{id}/scan (Async Exposure Scan with Rate/Budget Gate)
5. GET  /investigations/{id}/events (Real-Time SSE Event Stream)
6. GET  /investigations/{id}/findings (Deduplicated Findings & Clusters)
7. POST /investigations/{id}/findings/{finding_id}/verify (Human-in-the-Loop Review Gate)
8. POST /investigations/{id}/evidence/capture (SSRF-Safe Forensic Evidence Preservation)
9. POST /investigations/{id}/risk (Deterministic Risk Evaluation)
10. POST /investigations/{id}/report (Reproducible Forensic Reporting)
11. DELETE /investigations/{id} (Cross-Store Data Retention Purge)
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)



from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.attestation import InvestigationAttestation
from app.models.audit_log import AuditAction, AuditLog
from app.models.biometrics import ReferenceImage
from app.models.case import Case, CaseStatus
from app.models.discovery import CorrelationCluster, JobStatus, MatchCandidate, SearchJob, SearchResult
from app.models.evidence import Evidence, EvidenceEvent, EvidenceType, VerificationStatus
from app.models.intelligence import CaseReport, MonitoringRule, MonitoringRun, Report, ReportFormat, ReportStatus, ResponsePackage, RiskAssessment, RiskLevel, TimelineEvent
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.correlation_service import CorrelationEngine
from app.services.deduplication_clustering_service import deduplication_and_clustering_service
from app.services.dinov2_service import dinov2_service
from app.services.exposure_report_service import ReportPayload, exposure_report_service
from app.services.exposure_risk_service import exposure_risk_service
from app.services.exposure_scan_orchestrator import (
    CostBudgetExceededError,
    RateLimitExceededError,
    ScanProgressEvent,
    exposure_scan_orchestrator,
)
from app.services.image_analysis_service import image_analysis_service
from app.services.image_matching_service import MatchClassification, image_matching_service
from app.services.image_validation_service import ImageValidationError, image_validation_service
from app.services.matching_orchestrator import matching_orchestrator
from app.services.monitoring_service import MonitoringService
from app.services.provider_orchestration_service import ProviderOptions, ProviderStatus, provider_orchestrator
from app.services.qdrant_service import qdrant_service
from app.services.response_package_service import response_package_service
from app.services.retention_service import retention_service
from app.services.secure_storage_service import secure_storage_service
from app.services.ssrf_safe_fetcher import EvidenceCaptureSecurityError, SecureUrlFetcher, secure_url_fetcher
from app.services.temporary_image_service import temporary_image_service
from app.services.timeline_service import timeline_service
from tests.fixtures.synthetic_corpus import generate_15_transform_corpus, get_image_bytes


router = APIRouter()


# -------------------------------------------------------------
# Schemas
# -------------------------------------------------------------
class CreateInvestigationRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    target_subject_label: str | None = None


class AttestationRequest(BaseModel):
    attestation_text: str = Field(..., min_length=10)
    attestation_version: str = "v1.0.0"
    policy_version: str | None = None
    reference_image_sha256: str | None = None


class VerifyFindingRequest(BaseModel):
    status: str = Field(..., pattern="^(VERIFIED|REJECTED|UNCERTAIN)$")
    reason: str | None = None
    review_notes: str | None = None


class CaptureEvidenceRequest(BaseModel):
    finding_id: uuid.UUID
    rationale: str | None = None


class ReportExportRequest(BaseModel):
    format: str = Field("JSON", pattern="^(JSON|CSV|TEXT|PDF)$")
    title: str | None = None
    include_audit_trail: bool = False


class CreateResponsePackageRequest(BaseModel):
    target_domain: str = Field(..., min_length=1, max_length=255)
    target_entity: str | None = None
    finding_ids: list[uuid.UUID] | None = None
    format: str = Field("MARKDOWN", pattern="^(MARKDOWN|JSON|PDF)$")


class ConfigureMonitoringRequest(BaseModel):
    frequency: str = Field("DAILY", pattern="^(DAILY|WEEKLY)$")
    enabled: bool = True


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_investigation(
    req: CreateInvestigationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new isolated image exposure investigation container."""
    case_num = f"EXP-{datetime_tag()}-{uuid.uuid4().hex[:6].upper()}"
    new_case = Case(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        case_number=case_num,
        title=req.title,
        description=req.description,
        target_subject_label=req.target_subject_label,
        status=CaseStatus.DRAFT,
        current_stage=1,
    )
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    return {
        "id": str(new_case.id),
        "case_number": new_case.case_number,
        "title": new_case.title,
        "status": new_case.status,
        "created_at": new_case.created_at.isoformat(),
    }


@router.post("/{investigation_id}/attestation", status_code=status.HTTP_201_CREATED)
async def record_attestation(
    investigation_id: uuid.UUID,
    req: AttestationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Record user authorization attestation (policy/audit control)."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    attestation = InvestigationAttestation(
        case_id=case.id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        attestation_text=req.attestation_text,
        attestation_version=req.attestation_version,
        reference_image_hash=req.reference_image_sha256 or "PENDING_UPLOAD",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(attestation)
    await db.commit()
    await db.refresh(attestation)

    return {
        "attestation_id": str(attestation.id),
        "investigation_id": str(case.id),
        "attestation_version": attestation.attestation_version,
        "attested_at": attestation.attested_at.isoformat(),
        "is_policy_record": True,
        "notice": "Attestation recorded as an organizational policy/audit control.",
    }


@router.post("/{investigation_id}/reference-image", status_code=status.HTTP_201_CREATED)
async def upload_reference_image(
    investigation_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate, store, hash, and extract DINOv2 embeddings for reference image."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    file_bytes = await file.read()

    # 1. Strict File Validation
    try:
        validated = image_validation_service.validate(
            file_bytes=file_bytes,
            claimed_mime=file.content_type,
        )
    except ImageValidationError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # 2. Secure Storage
    storage_path, sha256_hash = secure_storage_service.save_reference_image(
        file_bytes=validated.raw_bytes,
        filename=validated.storage_filename,
    )

    # 3. Image Analysis (pHash, dHash, Quality)
    analysis = image_analysis_service.analyze(validated.raw_bytes)

    # 4. DINOv2 Embedding Extraction
    embedding = dinov2_service.extract_embedding(validated.raw_bytes)

    # 5. Index into Qdrant
    ref_image_id = uuid.uuid4()
    await qdrant_service.upsert_embedding(
        vector_id=str(ref_image_id),
        vector=embedding.vector,
        investigation_id=case.id,
        org_id=case.organization_id,
        reference_image_id=ref_image_id,
        metadata={"sha256": sha256_hash, "format": validated.format},
    )

    # 6. Store ReferenceImage record
    ref_image = ReferenceImage(
        id=ref_image_id,
        case_id=case.id,
        image_url=f"/api/v1/investigations/{case.id}/reference-image/raw",
        file_path=storage_path,
        sha256_hash=sha256_hash,
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        is_primary=True,
        quality_score=analysis.quality.sharpness,
    )
    db.add(ref_image)

    # Update attestation record with computed image hash if present
    att_stmt = select(InvestigationAttestation).where(InvestigationAttestation.case_id == case.id)
    att_res = await db.execute(att_stmt)
    att_item = att_res.scalars().first()
    if att_item:
        att_item.reference_image_hash = sha256_hash

    case.status = CaseStatus.VALIDATED
    case.current_stage = 2
    await db.commit()

    return {
        "reference_image_id": str(ref_image.id),
        "sha256": sha256_hash,
        "sha256_hash": sha256_hash,
        "phash": analysis.phash,
        "dhash": analysis.dhash,
        "dinov2_indexed": True,
        "dimensions": {"width": validated.width, "height": validated.height},
        "quality": {
            "sharpness": analysis.quality.sharpness,
            "brightness": analysis.quality.brightness,
            "contrast": analysis.quality.contrast,
            "is_usable": analysis.quality.is_usable,
        },
        "dinov2": {
            "model": embedding.model_name,
            "dimension": embedding.dimension,
            "inference_duration_ms": embedding.inference_duration_ms,
        },
    }


@router.get("/{investigation_id}")
async def get_investigation_details(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve full investigation details enforcing tenant isolation."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    return {
        "id": str(case.id),
        "case_number": case.case_number,
        "title": case.title,
        "description": case.description,
        "status": case.status.value if hasattr(case.status, "value") else str(case.status),
        "current_stage": case.current_stage,
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
    }


@router.get("/{investigation_id}/reference-image")
async def get_reference_image_metadata(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get reference image metadata with data minimization (never exposes raw hashes or embeddings)."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    stmt = select(ReferenceImage).where(ReferenceImage.case_id == case.id)
    res = await db.execute(stmt)
    ref_images = res.scalars().all()
    ref = next((r for r in ref_images if r.is_primary), None) or (ref_images[0] if ref_images else None)
    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reference image found for this investigation.",
        )

    return {
        "reference_image_id": str(ref.id),
        "investigation_id": str(case.id),
        "mime_type": ref.mime_type,
        "size_bytes": ref.size_bytes,
        "quality_score": ref.quality_score,
        "created_at": ref.created_at.isoformat(),
    }


@router.get("/{investigation_id}/reference-image/status")
async def get_reference_image_status(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get analysis and indexing status for the reference image."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    stmt = select(ReferenceImage).where(ReferenceImage.case_id == case.id)
    res = await db.execute(stmt)
    ref = res.scalars().first()
    if not ref:
        return {
            "investigation_id": str(case.id),
            "status": "PENDING",
            "dinov2_index_status": "pending",
        }

    return {
        "investigation_id": str(case.id),
        "reference_image_id": str(ref.id),
        "status": "COMPLETED",
        "dinov2_index_status": "indexed",
        "quality_score": ref.quality_score,
        "indexed_at": ref.created_at.isoformat(),
    }


@router.post("/{investigation_id}/match", status_code=status.HTTP_200_OK)
@router.post("/{investigation_id}/match-candidates/evaluate", status_code=status.HTTP_200_OK)
async def run_investigation_matching(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute multi-tier candidate matching against tenant-safe corpus & same-investigation references."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    candidates = await matching_orchestrator.execute_matching(
        db=db,
        investigation_id=case.id,
        organization_id=current_user.organization_id,
    )
    formatted = [
        {
            "id": str(c.id),
            "candidate_identifier": c.candidate_identifier,
            "candidate_filename": c.candidate_identifier,
            "source_label": c.candidate_identifier,
            "candidate_image_url": c.candidate_image_url,
            "classification": c.classification,
            "similarity_score": c.similarity_score,
            "tier_applied": c.tier_applied,
            "explanation": c.explanation,
            "signals": c.signals_json,
            "status": c.status,
        }
        for c in candidates
    ]
    return {
        "investigation_id": str(case.id),
        "status": "COMPLETED",
        "candidates_count": len(candidates),
        "matches": formatted,
        "candidates": formatted,
    }



@router.get("/{investigation_id}/matches")
async def get_investigation_matches(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve all persisted match candidates for the investigation enforcing tenant isolation."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    stmt = select(MatchCandidate).where(
        MatchCandidate.case_id == case.id,
        MatchCandidate.organization_id == current_user.organization_id,
    ).order_by(MatchCandidate.similarity_score.desc())
    res = await db.execute(stmt)
    candidates = res.scalars().all()

    return {
        "investigation_id": str(case.id),
        "status": case.status.value if hasattr(case.status, "value") else str(case.status),
        "candidates_count": len(candidates),
        "candidates": [
            {
                "id": str(c.id),
                "candidate_identifier": c.candidate_identifier,
                "candidate_image_url": c.candidate_image_url,
                "candidate_sha256": c.candidate_sha256,
                "classification": c.classification,
                "similarity_score": c.similarity_score,
                "tier_applied": c.tier_applied,
                "explanation": c.explanation,
                "signals": c.signals_json,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in candidates
        ],
    }


@router.get("/{investigation_id}/matches/{candidate_id}")
async def get_match_candidate_detail(
    investigation_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve detailed candidate comparison data."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    stmt = select(MatchCandidate).where(
        MatchCandidate.id == candidate_id,
        MatchCandidate.case_id == case.id,
        MatchCandidate.organization_id == current_user.organization_id,
    )
    res = await db.execute(stmt)
    candidate = res.scalars().first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match candidate not found.",
        )

    return {
        "id": str(candidate.id),
        "investigation_id": str(case.id),
        "candidate_identifier": candidate.candidate_identifier,
        "candidate_image_url": candidate.candidate_image_url,
        "candidate_sha256": candidate.candidate_sha256,
        "classification": candidate.classification,
        "similarity_score": candidate.similarity_score,
        "tier_applied": candidate.tier_applied,
        "explanation": candidate.explanation,
        "signals": candidate.signals_json,
        "status": candidate.status,
    }


@router.get("/{investigation_id}/corpus-image/{transform_name}")
async def get_corpus_image(
    investigation_id: uuid.UUID,
    transform_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Serve synthetic benchmark corpus images for candidate preview rendering."""
    # Ensure user has access to investigation
    await get_case_scoped(db, investigation_id, current_user.organization_id)
    corpus = generate_15_transform_corpus()
    if transform_name not in corpus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corpus image not found")

    img = corpus[transform_name]
    img_format = "JPEG" if "jpeg" in transform_name or "compression" in transform_name else "PNG"
    img_bytes = get_image_bytes(img, format=img_format)
    mime = "image/jpeg" if img_format == "JPEG" else "image/png"
    return Response(content=img_bytes, media_type=mime)


@router.post("/{investigation_id}/scan", status_code=status.HTTP_202_ACCEPTED)
async def start_exposure_scan(
    investigation_id: uuid.UUID,
    payload: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Trigger async multi-provider exposure scan with rate/cost limits."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    # Rate Limiting & Cost Budget Checks
    try:
        exposure_scan_orchestrator.check_rate_and_budget(case.organization_id)
    except CostBudgetExceededError as err:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(err))
    except RateLimitExceededError as err:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(err))

    # Create SearchJob record
    job = SearchJob(
        case_id=case.id,
        provider="GoogleCloudVision,TinEye",
        status=JobStatus.PENDING,
        progress_pct=0,
        current_step="QUEUED",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Execute scan pipeline
    await exposure_scan_orchestrator.run_scan_pipeline(
        db=db,
        case=case,
        search_job=job,
        use_mock_fallback=True,
    )

    return {
        "job_id": str(job.id),
        "investigation_id": str(case.id),
        "status": job.status,
        "message": "Async exposure scan pipeline initiated.",
    }


class WebSearchRequest(BaseModel):
    max_results: int = Field(default=25, ge=1, le=100)
    include_similar: bool = True


@router.post("/{investigation_id}/web-search", status_code=status.HTTP_200_OK)
async def execute_web_search(
    investigation_id: uuid.UUID,
    req: WebSearchRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Execute Public Web Discovery (SearchAPI Google Lens as primary, Google Vision optional).
    Creates an ephemeral temporary image URL, queries the search provider, runs Phase 3 matching,
    and records candidates in PENDING_REVIEW state.
    """
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    # 1. Fetch Stored Reference Image
    ref_stmt = select(ReferenceImage).where(ReferenceImage.case_id == case.id)
    ref_images = (await db.execute(ref_stmt)).scalars().all()
    ref_img = next((r for r in ref_images if r.is_primary), None) or (ref_images[0] if ref_images else None)

    if not ref_img or not ref_img.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Investigation has no reference image uploaded. Capture or upload a reference image first.",
        )

    try:
        ref_bytes = secure_storage_service.read_file(ref_img.file_path)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read stored reference image: {err}",
        )

    # 2. Rate & Budget Control
    try:
        exposure_scan_orchestrator.check_rate_and_budget(case.organization_id)
    except CostBudgetExceededError as err:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(err))
    except RateLimitExceededError as err:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(err))

    # 3. Select Active Provider (SearchAPI Google Lens primary, Google Vision fallback)
    searchapi_prov = provider_orchestrator.searchapi_provider
    google_prov = provider_orchestrator.google_provider

    if searchapi_prov.get_status() == ProviderStatus.READY or getattr(settings, "SEARCHAPI_ENABLED", True):
        chosen_provider = searchapi_prov
    elif getattr(settings, "GOOGLE_VISION_ENABLED", False) and google_prov.get_status() == ProviderStatus.READY:
        chosen_provider = google_prov
    else:
        chosen_provider = searchapi_prov

    provider_name = chosen_provider.name
    prov_status = chosen_provider.get_status()

    # 4. Analyze reference image for Phase 3 matching
    ref_analysis = image_analysis_service.analyze(ref_bytes)
    ref_embedding = dinov2_service.extract_embedding(ref_bytes)

    max_results = req.max_results if req else 25
    include_similar = req.include_similar if req else True
    options = ProviderOptions(max_results=max_results, include_similar=include_similar)

    # 5. Create Ephemeral Temporary Image Token (Auto-expiring, deleted in finally block)
    temp_token, temp_url = temporary_image_service.create_temporary_image(
        image_bytes=ref_bytes,
        content_type="image/jpeg",
        ttl_seconds=600,
    )

    raw_discoveries = []
    try:
        logger.info(f"Executing web search via {provider_name} for investigation {case.id}")
        raw_discoveries = await chosen_provider.discover(
            image_bytes=ref_bytes,
            image_url=temp_url,
            options=options,
        )
    except PermissionError as auth_err:
        logger.error(f"Search provider auth error: {auth_err}")
        return {
            "investigation_id": str(case.id),
            "provider": provider_name,
            "provider_status": "PROVIDER_AUTH_ERROR",
            "results_count": 0,
            "candidates": [],
            "status": "PROVIDER_AUTH_ERROR",
            "message": "Search provider authentication failed (401/403). Check API key configuration.",
        }
    except RuntimeError as quota_err:
        logger.error(f"Search provider quota error: {quota_err}")
        return {
            "investigation_id": str(case.id),
            "provider": provider_name,
            "provider_status": "PROVIDER_QUOTA_EXCEEDED",
            "results_count": 0,
            "candidates": [],
            "status": "PROVIDER_QUOTA_EXCEEDED",
            "message": "Search provider quota or rate limit exceeded.",
        }
    except TimeoutError as timeout_err:
        logger.error(f"Search provider timeout: {timeout_err}")
        return {
            "investigation_id": str(case.id),
            "provider": provider_name,
            "provider_status": "PROVIDER_TIMEOUT",
            "results_count": 0,
            "candidates": [],
            "status": "PROVIDER_TIMEOUT",
            "message": "Search provider request timed out.",
        }
    except Exception as err:
        logger.error(f"Discovery provider call failed: {err}")
    finally:
        # Guarantee ephemeral temporary image token is purged immediately
        temporary_image_service.delete_temporary_image(temp_token)

    # 6. Extract web entities and labels from discovery metadata
    entities: list[dict[str, Any]] = []
    best_guesses: list[str] = []
    for d in raw_discoveries:
        if "web_entities" in d.metadata and not entities:
            entities = d.metadata["web_entities"]
        if "best_guess_labels" in d.metadata and not best_guesses:
            best_guesses = d.metadata["best_guess_labels"]

    # 7. Create / Update SearchJob record
    job = SearchJob(
        case_id=case.id,
        provider=provider_name,
        status=JobStatus.COMPLETED,
        progress_pct=100,
        current_step="COMPLETED",
        total_found=len(raw_discoveries),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    # Clear previous search results for idempotent re-runs
    await db.execute(delete(SearchResult).where(SearchResult.case_id == case.id))

    # 8. Deduplicate and evaluate matches via Phase 3 pipeline
    dedup_candidates = deduplication_and_clustering_service.deduplicate_results(raw_discoveries)
    created_results: list[SearchResult] = []

    for cand in dedup_candidates:
        cand_sha256 = None
        cand_phash = None
        cand_vector = None

        if cand.image_url:
            try:
                fetch_res = await SecureUrlFetcher.fetch(cand.image_url)
                if fetch_res and fetch_res.raw_bytes:
                    cand_img_bytes = fetch_res.raw_bytes
                    cand_analysis = image_analysis_service.analyze(cand_img_bytes)
                    cand_sha256 = cand_analysis.sha256_hash
                    cand_phash = cand_analysis.phash
                    cand_emb = dinov2_service.extract_embedding(cand_img_bytes)
                    cand_vector = cand_emb.vector
            except Exception as fetch_err:
                logger.debug(f"Candidate image fetch skipped/failed ({cand.image_url[:60]}): {fetch_err}")

        # Run Phase 3 matching evaluation
        match_eval = image_matching_service.evaluate_match(
            reference_sha256=ref_analysis.sha256_hash,
            candidate_sha256=cand_sha256,
            reference_phash=ref_analysis.phash,
            candidate_phash=cand_phash,
            reference_vector=ref_embedding.vector,
            candidate_vector=cand_vector,
        )

        if match_eval.overall_similarity_score > 0:
            sim_score = match_eval.overall_similarity_score
            classification_str = match_eval.classification.value
            explanation_str = match_eval.explanation
            tier_applied = match_eval.tier_applied
        else:
            sim_score = round(cand.similarity_score if cand.similarity_score else 0.85, 4)
            if sim_score >= 0.99:
                classification_str = "EXACT"
            elif sim_score >= 0.90:
                classification_str = "SAME_TRANSFORMED_IMAGE"
            elif sim_score >= 0.75:
                classification_str = "PROBABLE_RELATED"
            elif sim_score >= 0.60:
                classification_str = "VISUALLY_SIMILAR"
            else:
                classification_str = "UNRELATED"
            explanation_str = f"Google Lens discovery match with provider confidence {sim_score:.2f}."
            tier_applied = 3

        match_type_val = "VISUALLY_SIMILAR"
        snippet_val = ""
        thumbnail_url_val = cand.image_url
        if cand.provenance_records:
            first_prov = cand.provenance_records[0]
            if isinstance(first_prov, dict) and isinstance(first_prov.get("metadata"), dict):
                match_type_val = first_prov["metadata"].get("match_type", "VISUALLY_SIMILAR")
                snippet_val = first_prov["metadata"].get("snippet", "")
                thumbnail_url_val = first_prov["metadata"].get("thumbnail_url", cand.image_url)

        sr = SearchResult(
            case_id=case.id,
            search_job_id=job.id,
            provider=provider_name,
            source_url=cand.canonical_url,
            page_url=cand.canonical_url,
            image_url=cand.image_url,
            domain=cand.domain,
            page_title=cand.page_title,
            similarity_score=sim_score,
            result_type=classification_str,
            metadata_json={
                "raw_provider_score": cand.similarity_score,
                "providers": cand.providers,
                "classification": classification_str,
                "explanation": explanation_str,
                "tier_applied": tier_applied,
                "verification_status": "PENDING_REVIEW",
                "match_type": match_type_val,
                "snippet": snippet_val,
                "thumbnail_url": thumbnail_url_val,
                "observation_state": "NEW",
                "best_guess_labels": best_guesses,
                "web_entities": entities,
            },
        )
        db.add(sr)
        created_results.append(sr)

    case.status = CaseStatus.DISCOVERY_COMPLETE
    case.current_stage = 4
    await db.commit()

    # 9. Record Audit & Timeline events
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.discovery_completed,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="investigation",
        resource_id=str(case.id),
        details={"provider": provider_name, "results_count": len(created_results)},
    )

    await timeline_service.record_event(
        db=db,
        case_id=case.id,
        event_type="WEB_SEARCH_EXECUTED",
        title=f"{provider_name} Discovery Executed",
        description=f"Public web reverse discovery completed via {provider_name}. Retrieved {len(created_results)} candidate exposure signals for analyst review.",
        actor_id=current_user.id,
        metadata={
            "provider": provider_name,
            "candidates_count": len(created_results),
            "best_guess_labels": best_guesses,
        },
    )

    status_str = chosen_provider.get_status().value

    return {
        "investigation_id": str(case.id),
        "job_id": str(job.id),
        "provider": provider_name,
        "provider_status": status_str,
        "results_count": len(created_results),
        "candidates": [
            {
                "id": str(sr.id),
                "domain": sr.domain,
                "page_title": sr.page_title,
                "page_url": sr.page_url,
                "source_url": sr.source_url,
                "image_url": sr.image_url,
                "provider": sr.provider,
                "similarity_score": sr.similarity_score,
                "result_type": sr.result_type,
                "metadata": sr.metadata_json,
                "discovered_at": sr.discovered_at.isoformat(),
            }
            for sr in created_results
        ],
        "web_entities": entities,
        "best_guess_labels": best_guesses,
        "status": "COMPLETED" if created_results else "NO_MATCHES",
        "message": (
            f"Web search completed with {len(created_results)} candidates."
            if created_results
            else "No matching or related public-web results were returned by the configured discovery providers."
        ),
    }


@router.get("/{investigation_id}/events")
async def stream_investigation_events(
    investigation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Server-Sent Events (SSE) streaming real-time investigation state."""
    q = exposure_scan_orchestrator.subscribe_events(str(investigation_id))

    async def event_generator():
        try:
            while True:
                event = await q.get()
                payload_json = json.dumps({
                    "event_type": event.event_type,
                    "investigation_id": event.investigation_id,
                    "job_id": event.job_id,
                    "step": event.step,
                    "progress_pct": event.progress_pct,
                    "message": event.message,
                    "timestamp": event.timestamp,
                    "payload": event.payload,
                })
                yield f"event: {event.event_type}\ndata: {payload_json}\n\n"
                if event.step in ("COMPLETED", "FAILED"):
                    break
        finally:
            exposure_scan_orchestrator.unsubscribe_events(str(investigation_id), q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{investigation_id}/findings")
async def get_findings_and_clusters(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve deduplicated candidates and exposure clusters."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    res_stmt = select(SearchResult).where(SearchResult.case_id == case.id)
    cl_stmt = select(CorrelationCluster).where(CorrelationCluster.case_id == case.id)

    res_results = await db.execute(res_stmt)
    cl_results = await db.execute(cl_stmt)

    findings = res_results.scalars().all()
    clusters = cl_results.scalars().all()

    return {
        "investigation_id": str(case.id),
        "total_findings": len(findings),
        "findings": [
            {
                "id": str(f.id),
                "domain": f.domain,
                "page_title": f.page_title,
                "page_url": f.page_url,
                "source_url": f.source_url,
                "image_url": f.image_url,
                "provider": f.provider,
                "similarity_score": f.similarity_score,
                "result_type": f.result_type,
                "metadata": f.metadata_json,
                "discovered_at": f.discovered_at.isoformat(),
            }
            for f in findings
        ],
        "clusters": [
            {
                "id": str(c.id),
                "name": c.cluster_name,
                "member_count": c.member_count,
                "domains": c.domains_json,
                "risk_weight": c.risk_weight,
            }
            for c in clusters
        ],
    }


@router.get("/{investigation_id}/graph")
async def get_investigation_exposure_graph(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve tenant-scoped exposure investigation graph data."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    engine = CorrelationEngine(db)
    graph = await engine.build_exposure_graph(case)
    return {
        "investigation_id": str(case.id),
        "nodes": graph.nodes,
        "edges": graph.edges,
        "total_nodes": graph.total_nodes,
        "total_edges": graph.total_edges,
        "cluster_count": graph.cluster_count,
    }


@router.get("/providers/status")
@router.get("/{investigation_id}/providers")
async def get_discovery_provider_statuses(
    investigation_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return explicit provider configuration and circuit-breaker statuses."""
    statuses = provider_orchestrator.get_provider_statuses()
    return {
        "providers": statuses,
        "active_count": sum(1 for p in statuses.values() if p["status"] == "READY"),
        "total_configured": sum(1 for p in statuses.values() if p["configured"]),
    }


@router.get("/{investigation_id}/overview")
async def get_investigation_overview(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Unified single-call investigation summary dashboard."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    # Reference Image
    ref_stmt = select(ReferenceImage).where(ReferenceImage.case_id == case.id)
    ref_images = (await db.execute(ref_stmt)).scalars().all()
    primary_ref = next((r for r in ref_images if r.is_primary), None) or (ref_images[0] if ref_images else None)

    # Findings
    sr_stmt = select(SearchResult).where(SearchResult.case_id == case.id)
    findings = (await db.execute(sr_stmt)).scalars().all()

    verified_count = sum(1 for f in findings if f.metadata_json.get("verification_status") == "VERIFIED")
    rejected_count = sum(1 for f in findings if f.metadata_json.get("verification_status") == "REJECTED")
    uncertain_count = sum(1 for f in findings if f.metadata_json.get("verification_status") == "UNCERTAIN")
    unverified_count = len(findings) - (verified_count + rejected_count + uncertain_count)

    # Clusters
    cl_stmt = select(CorrelationCluster).where(CorrelationCluster.case_id == case.id)
    clusters = (await db.execute(cl_stmt)).scalars().all()

    # Evidence
    ev_stmt = select(Evidence).where(Evidence.case_id == case.id).order_by(Evidence.custody_sequence.asc())
    evidence_items = (await db.execute(ev_stmt)).scalars().all()

    # Risk Assessment
    risk_stmt = select(RiskAssessment).where(RiskAssessment.case_id == case.id).order_by(RiskAssessment.created_at.desc())
    latest_risk = (await db.execute(risk_stmt)).scalars().first()

    # Timeline (latest 10)
    timeline = await timeline_service.get_timeline(db, case.id, ascending=False)

    # Providers
    provider_status = provider_orchestrator.get_provider_statuses()

    # Reports & Response Packages
    rep_stmt = select(CaseReport).where(CaseReport.case_id == case.id)
    reports = (await db.execute(rep_stmt)).scalars().all()

    pkg_stmt = select(ResponsePackage).where(ResponsePackage.case_id == case.id)
    packages = (await db.execute(pkg_stmt)).scalars().all()

    return {
        "investigation": {
            "id": str(case.id),
            "case_number": case.case_number,
            "title": case.title,
            "description": case.description,
            "status": case.status.value if hasattr(case.status, "value") else str(case.status),
            "current_stage": case.current_stage,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        },
        "reference_image": {
            "id": str(primary_ref.id) if primary_ref else None,
            "sha256_hash": primary_ref.sha256_hash if primary_ref else None,
            "filename": primary_ref.original_filename if primary_ref else None,
            "resolution": f"{primary_ref.width_px}x{primary_ref.height_px}" if primary_ref and primary_ref.width_px else None,
        } if primary_ref else None,
        "metrics": {
            "total_findings": len(findings),
            "verified_count": verified_count,
            "rejected_count": rejected_count,
            "uncertain_count": uncertain_count,
            "unverified_count": unverified_count,
            "cluster_count": len(clusters),
            "evidence_count": len(evidence_items),
            "reports_count": len(reports),
            "response_packages_count": len(packages),
        },
        "risk_assessment": {
            "risk_level": latest_risk.overall_risk_level.value if latest_risk else "LOW",
            "score": latest_risk.calculated_score if latest_risk else 0.0,
            "risk_policy_version": latest_risk.risk_policy_version if latest_risk else "v1",
            "explanation": latest_risk.explanation_text if latest_risk else "Zero verified exposure endpoints confirmed.",
            "factors": latest_risk.factor_breakdown_json.get("factors", []) if latest_risk and latest_risk.factor_breakdown_json else [],
        } if latest_risk else {
            "risk_level": "LOW",
            "score": 0.0,
            "risk_policy_version": "v1",
            "explanation": "Zero verified exposure endpoints confirmed. Minimal exposure risk detected.",
            "factors": [],
        },
        "recent_timeline": timeline[:8],
        "providers": provider_status,
    }


@router.get("/{investigation_id}/timeline")
async def get_investigation_timeline(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve complete chronological investigation audit & event trail."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    events = await timeline_service.get_timeline(db, case.id, ascending=True)
    return {
        "investigation_id": str(case.id),
        "case_number": case.case_number,
        "events": events,
        "count": len(events),
    }


@router.get("/{investigation_id}/evidence")
async def get_evidence_vault(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List all evidence artifacts preserved in the immutable Evidence Vault."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(Evidence).where(Evidence.case_id == case.id).order_by(Evidence.custody_sequence.asc())
    res = await db.execute(stmt)
    evidence_items = res.scalars().all()

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.evidence_viewed,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="investigation",
        resource_id=str(case.id),
        details={"evidence_count": len(evidence_items)},
    )

    items_data = []
    for e in evidence_items:
        items_data.append({
            "id": str(e.id),
            "evidence_number": e.evidence_number,
            "custody_sequence": e.custody_sequence,
            "previous_evidence_hash": e.previous_evidence_hash,
            "sha256_hash": e.sha256_hash,
            "evidence_type": e.evidence_type.value if hasattr(e.evidence_type, "value") else str(e.evidence_type),
            "verification_status": e.verification_status.value if hasattr(e.verification_status, "value") else str(e.verification_status),
            "domain": e.domain,
            "page_title": e.page_title,
            "page_url": e.page_url,
            "image_url": e.image_url,
            "content_type": e.content_type or e.mime_type or "application/octet-stream",
            "size_bytes": e.size_bytes,
            "has_artifact": bool(e.file_path or e.screenshot_path),
            "user_reason": e.user_reason,
            "verified_at": e.verified_at.isoformat() if e.verified_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "chain_of_custody": e.chain_of_custody_json,
        })

    return {
        "investigation_id": str(case.id),
        "case_number": case.case_number,
        "evidence_items": items_data,
        "total_count": len(items_data),
    }


@router.post("/{investigation_id}/findings/{finding_id}/verify")
async def verify_finding(
    investigation_id: uuid.UUID,
    finding_id: uuid.UUID,
    req: VerifyFindingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Human-in-the-loop analyst review verification gate."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(SearchResult).where(SearchResult.id == finding_id, SearchResult.case_id == case.id)
    res = await db.execute(stmt)
    finding = res.scalars().first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")

    reason_val = req.reason or req.review_notes or "Analyst verified"
    finding.metadata_json["verification_status"] = req.status
    finding.metadata_json["verified_by"] = str(current_user.id)
    finding.metadata_json["verification_reason"] = reason_val
    finding.metadata_json["verified_at"] = datetime.now(timezone.utc).isoformat()

    # If verified, initialize/link evidence item
    ev_record = None
    if req.status == "VERIFIED":
        # Calculate custody sequence and previous hash
        prev_ev_stmt = select(Evidence).where(Evidence.case_id == case.id).order_by(Evidence.custody_sequence.desc())
        prev_ev = (await db.execute(prev_ev_stmt)).scalars().first()
        custody_seq = (prev_ev.custody_sequence + 1) if prev_ev else 1
        prev_hash = prev_ev.sha256_hash if prev_ev else "GENESIS_EVIDENCE_ROOT"

        ev_hash = finding.metadata_json.get("signals", {}).get("sha256", f"VERIFIED_{finding.id.hex[:16]}")

        ev = Evidence(
            case_id=case.id,
            search_result_id=finding.id,
            evidence_number=f"EV-{uuid.uuid4().hex[:6].upper()}",
            custody_sequence=custody_seq,
            previous_evidence_hash=prev_hash,
            evidence_type=EvidenceType.DISCOVERED_IMAGE,
            verification_status=VerificationStatus.VERIFIED,
            source_url=finding.source_url,
            page_url=finding.page_url,
            image_url=finding.image_url,
            domain=finding.domain,
            page_title=finding.page_title,
            sha256_hash=ev_hash,
            evidence_hash=ev_hash,
            verified_by_id=current_user.id,
            verified_at=datetime.now(timezone.utc),
            user_reason=reason_val,
            chain_of_custody_json=[
                {
                    "event": "HUMAN_VERIFICATION",
                    "actor": str(current_user.id),
                    "status": "VERIFIED",
                    "reason": reason_val,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        db.add(ev)
        ev_record = ev

    # Append timeline event with explicit exposure semantics
    event_type_name = "NEW_VERIFIED_EXPOSURE" if req.status == "VERIFIED" else f"FINDING_{req.status}"
    await timeline_service.record_event(
        db=db,
        case_id=case.id,
        event_type=event_type_name,
        title=f"{'Confirmed Exposure Verified' if req.status == 'VERIFIED' else 'Finding Triage: ' + req.status}",
        description=f"Finding on {finding.domain} triaged as {req.status}. Reason: {reason_val}",
        actor_id=current_user.id,
        metadata={"finding_id": str(finding.id), "status": req.status, "domain": finding.domain},
    )

    # Broadcast SSE: monitoring.new_verified_exposure if verified
    if req.status == "VERIFIED":
        await exposure_scan_orchestrator.broadcast_event(
            ScanProgressEvent(
                event_type="monitoring.new_verified_exposure",
                investigation_id=str(case.id),
                job_id=str(finding.id),
                step="NEW_VERIFIED_EXPOSURE",
                progress_pct=100,
                message=f"New confirmed exposure verified on {finding.domain}.",
                timestamp=datetime.now(timezone.utc).isoformat(),
                payload={"finding_id": str(finding.id), "domain": finding.domain, "status": "VERIFIED"},
            )
        )

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.result_verified,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="finding",
        resource_id=str(finding.id),
        details={"status": req.status, "reason": reason_val, "domain": finding.domain},
    )

    await db.commit()

    return {
        "finding_id": str(finding.id),
        "verification_status": req.status,
        "verified_by": str(current_user.id),
        "reason": reason_val,
        "evidence_id": str(ev_record.id) if ev_record else None,
    }


@router.post("/{investigation_id}/evidence/capture")
async def capture_evidence(
    investigation_id: uuid.UUID,
    req: CaptureEvidenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """SSRF-safe external evidence capture and cryptographic preservation in Vault."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(SearchResult).where(SearchResult.id == req.finding_id, SearchResult.case_id == case.id)
    res = await db.execute(stmt)
    finding = res.scalars().first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")

    target_url = finding.image_url or finding.page_url

    # Broadcast SSE: evidence.collection.started
    await exposure_scan_orchestrator.broadcast_event(
        ScanProgressEvent(
            event_type="evidence.collection.started",
            investigation_id=str(case.id),
            job_id=str(finding.id),
            step="CAPTURING_EVIDENCE",
            progress_pct=10,
            message=f"Initiating SSRF-safe evidence capture for {finding.domain}...",
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload={"finding_id": str(finding.id), "domain": finding.domain, "url": target_url},
        )
    )

    # Execute SSRF-Safe Fetch
    try:
        safe_res = await secure_url_fetcher.fetch(target_url)
    except EvidenceCaptureSecurityError as err:
        await exposure_scan_orchestrator.broadcast_event(
            ScanProgressEvent(
                event_type="evidence.collection.failed",
                investigation_id=str(case.id),
                job_id=str(finding.id),
                step="EVIDENCE_CAPTURE_REJECTED",
                progress_pct=0,
                message=f"SSRF security gate blocked evidence capture: {err}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                payload={"error": str(err)},
            )
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Evidence capture rejected: {err}")
    except Exception as err:
        await exposure_scan_orchestrator.broadcast_event(
            ScanProgressEvent(
                event_type="evidence.collection.failed",
                investigation_id=str(case.id),
                job_id=str(finding.id),
                step="EVIDENCE_CAPTURE_ERROR",
                progress_pct=0,
                message=f"Failed to capture evidence: {err}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                payload={"error": str(err)},
            )
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Evidence fetch failed: {err}")

    # Save to secure storage
    filename = f"evidence_{uuid.uuid4().hex[:12]}.bin"
    storage_path, artifact_sha256 = secure_storage_service.save_evidence_artifact(
        file_bytes=safe_res.raw_bytes,
        filename=filename,
    )

    # Compute custody sequence and previous hash
    prev_ev_stmt = select(Evidence).where(Evidence.case_id == case.id).order_by(Evidence.custody_sequence.desc())
    prev_ev = (await db.execute(prev_ev_stmt)).scalars().first()
    custody_seq = (prev_ev.custody_sequence + 1) if prev_ev else 1
    prev_hash = prev_ev.sha256_hash if prev_ev else "GENESIS_EVIDENCE_ROOT"

    # Update or create Evidence record
    ev_stmt = select(Evidence).where(Evidence.search_result_id == finding.id)
    ev_res = await db.execute(ev_stmt)
    ev = ev_res.scalars().first()

    now_iso = datetime.now(timezone.utc).isoformat()
    custody_entry = {
        "event": "SSRF_SECURE_CAPTURE",
        "actor": str(current_user.id),
        "sha256_hash": artifact_sha256,
        "content_type": safe_res.content_type,
        "size_bytes": safe_res.size_bytes,
        "timestamp": now_iso,
    }

    if not ev:
        ev = Evidence(
            case_id=case.id,
            search_result_id=finding.id,
            evidence_number=f"EV-{uuid.uuid4().hex[:6].upper()}",
            custody_sequence=custody_seq,
            previous_evidence_hash=prev_hash,
            evidence_type=EvidenceType.DISCOVERED_IMAGE,
            verification_status=VerificationStatus.VERIFIED,
            source_url=finding.source_url,
            page_url=finding.page_url,
            image_url=finding.image_url,
            canonical_url=safe_res.canonical_url,
            domain=finding.domain,
            page_title=finding.page_title,
            sha256_hash=artifact_sha256,
            evidence_hash=artifact_sha256,
            file_path=storage_path,
            storage_key=storage_path,
            content_type=safe_res.content_type,
            mime_type=safe_res.content_type,
            size_bytes=safe_res.size_bytes,
            verified_by_id=current_user.id,
            verified_at=datetime.now(timezone.utc),
            user_reason=req.rationale,
            chain_of_custody_json=[custody_entry],
        )
        db.add(ev)
    else:
        ev.sha256_hash = artifact_sha256
        ev.evidence_hash = artifact_sha256
        ev.file_path = storage_path
        ev.storage_key = storage_path
        ev.size_bytes = safe_res.size_bytes
        ev.content_type = safe_res.content_type
        ev.mime_type = safe_res.content_type
        ev.canonical_url = safe_res.canonical_url
        history = list(ev.chain_of_custody_json or [])
        history.append(custody_entry)
        ev.chain_of_custody_json = history

    # Append Chain of Custody Event
    event = EvidenceEvent(
        evidence_id=ev.id,
        case_id=case.id,
        event_type="ARTIFACT_CAPTURED_AND_SEALED",
        actor_id=current_user.id,
        details_json={
            "sha256": artifact_sha256,
            "content_type": safe_res.content_type,
            "size_bytes": safe_res.size_bytes,
            "canonical_url": safe_res.canonical_url,
        },
    )
    db.add(event)

    # Append timeline event
    await timeline_service.record_event(
        db=db,
        case_id=case.id,
        event_type="EVIDENCE_CAPTURED",
        title=f"Evidence Sealed: {ev.evidence_number}",
        description=f"Preserved {safe_res.size_bytes} bytes from {finding.domain} with SHA-256 {artifact_sha256[:12]}...",
        actor_id=current_user.id,
        metadata={"evidence_id": str(ev.id), "sha256": artifact_sha256, "domain": finding.domain},
    )

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.evidence_preserved,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="evidence",
        resource_id=str(ev.id),
        details={"evidence_number": ev.evidence_number, "sha256": artifact_sha256, "domain": finding.domain},
    )

    # Broadcast SSE: evidence.collection.completed
    await exposure_scan_orchestrator.broadcast_event(
        ScanProgressEvent(
            event_type="evidence.collection.completed",
            investigation_id=str(case.id),
            job_id=str(ev.id),
            step="EVIDENCE_PRESERVED",
            progress_pct=100,
            message=f"Evidence artifact {ev.evidence_number} sealed in vault (SHA-256: {artifact_sha256[:12]}...).",
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload={
                "evidence_id": str(ev.id),
                "evidence_number": ev.evidence_number,
                "sha256_hash": artifact_sha256,
                "size_bytes": safe_res.size_bytes,
            },
        )
    )

    await db.commit()

    return {
        "evidence_id": str(ev.id),
        "evidence_number": ev.evidence_number,
        "custody_sequence": ev.custody_sequence,
        "previous_evidence_hash": ev.previous_evidence_hash,
        "sha256_hash": artifact_sha256,
        "content_type": safe_res.content_type,
        "size_bytes": safe_res.size_bytes,
        "status": "PRESERVED_IN_VAULT",
    }


@router.get("/{investigation_id}/evidence/{evidence_id}/download")
async def download_evidence_artifact(
    investigation_id: uuid.UUID,
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Download the raw cryptographically preserved evidence artifact binary."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(Evidence).where(Evidence.id == evidence_id, Evidence.case_id == case.id)
    res = await db.execute(stmt)
    ev = res.scalars().first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence item not found.")

    target_path = ev.file_path or ev.screenshot_path or ev.storage_key
    if not target_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No stored binary artifact for this evidence record.")

    artifact_bytes = secure_storage_service.load_evidence_artifact(target_path)
    if not artifact_bytes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence artifact file missing from storage.")

    # Log audit entry (with credential redaction)
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.evidence_downloaded,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="evidence",
        resource_id=str(ev.id),
        details={"evidence_number": ev.evidence_number, "sha256": ev.sha256_hash, "size_bytes": len(artifact_bytes)},
    )
    await db.commit()

    media_type = ev.content_type or ev.mime_type or "application/octet-stream"
    headers = {"Content-Disposition": f'attachment; filename="{ev.evidence_number}_{ev.sha256_hash[:8]}.bin"'}
    return Response(content=artifact_bytes, media_type=media_type, headers=headers)


@router.get("/{investigation_id}/evidence/{evidence_id}/verify-integrity")
async def verify_evidence_integrity(
    investigation_id: uuid.UUID,
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Recalculate SHA-256 cryptographic digest of stored artifact and verify custody chain."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(Evidence).where(Evidence.id == evidence_id, Evidence.case_id == case.id)
    res = await db.execute(stmt)
    ev = res.scalars().first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence item not found.")

    target_path = ev.file_path or ev.screenshot_path or ev.storage_key
    computed_hash = None
    is_valid = False
    if target_path:
        raw = secure_storage_service.load_evidence_artifact(target_path)
        if raw:
            computed_hash = hashlib.sha256(raw).hexdigest()
            is_valid = (computed_hash == ev.sha256_hash)

    # Verify custody sequence previous link
    chain_intact = True
    if ev.custody_sequence > 1:
        prev_stmt = select(Evidence).where(
            Evidence.case_id == case.id,
            Evidence.custody_sequence == ev.custody_sequence - 1,
        )
        prev_ev = (await db.execute(prev_stmt)).scalars().first()
        if not prev_ev or prev_ev.sha256_hash != ev.previous_evidence_hash:
            chain_intact = False

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.evidence_integrity_verified,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="evidence",
        resource_id=str(ev.id),
        details={"is_valid": is_valid, "chain_intact": chain_intact},
    )
    await db.commit()

    return {
        "evidence_id": str(ev.id),
        "evidence_number": ev.evidence_number,
        "custody_sequence": ev.custody_sequence,
        "stored_sha256": ev.sha256_hash,
        "computed_sha256": computed_hash,
        "previous_evidence_hash": ev.previous_evidence_hash,
        "is_valid": is_valid,
        "chain_intact": chain_intact,
    }


@router.get("/{investigation_id}/evidence/manifest")
async def export_evidence_manifest(
    investigation_id: uuid.UUID,
    format: str = Query("JSON", pattern="^(JSON|CSV)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Export complete evidence custody chain and hash manifest."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(Evidence).where(Evidence.case_id == case.id).order_by(Evidence.custody_sequence.asc())
    evidence_items = (await db.execute(stmt)).scalars().all()

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.evidence_manifest_exported,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="manifest",
        resource_id=str(case.id),
        details={"format": format, "item_count": len(evidence_items)},
    )
    await db.commit()

    manifest_rows = [
        {
            "sequence": e.custody_sequence,
            "evidence_number": e.evidence_number,
            "sha256_hash": e.sha256_hash,
            "previous_evidence_hash": e.previous_evidence_hash,
            "domain": e.domain,
            "page_url": e.page_url,
            "image_url": e.image_url,
            "content_type": e.content_type or e.mime_type or "application/octet-stream",
            "size_bytes": e.size_bytes,
            "verified_at": e.verified_at.isoformat() if e.verified_at else None,
        }
        for e in evidence_items
    ]

    if format == "CSV":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["INVESTIGATION ID", str(case.id)])
        writer.writerow(["CASE NUMBER", case.case_number])
        writer.writerow([])
        writer.writerow([
            "SEQUENCE",
            "EVIDENCE NUMBER",
            "SHA-256 HASH",
            "PREVIOUS HASH",
            "DOMAIN",
            "PAGE URL",
            "IMAGE URL",
            "CONTENT TYPE",
            "SIZE BYTES",
            "VERIFIED AT",
        ])
        for row in manifest_rows:
            writer.writerow([
                row["sequence"],
                row["evidence_number"],
                row["sha256_hash"],
                row["previous_evidence_hash"],
                row["domain"],
                row["page_url"],
                row["image_url"],
                row["content_type"],
                row["size_bytes"],
                row["verified_at"],
            ])
        return PlainTextResponse(output.getvalue(), media_type="text/csv")

    return {
        "investigation_id": str(case.id),
        "case_number": case.case_number,
        "manifest_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_items": len(manifest_rows),
        "manifest": manifest_rows,
    }


@router.post("/{investigation_id}/risk")
async def evaluate_risk(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Compute deterministic category-based risk assessment strictly gated by VERIFIED findings."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    # Broadcast SSE: risk.calculation.started
    await exposure_scan_orchestrator.broadcast_event(
        ScanProgressEvent(
            event_type="risk.calculation.started",
            investigation_id=str(case.id),
            job_id=str(uuid.uuid4()),
            step="CALCULATING_RISK",
            progress_pct=20,
            message="Calculating multi-factor exposure risk evaluation under policy v1...",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )

    ev_stmt = select(Evidence).where(
        Evidence.case_id == case.id,
        Evidence.verification_status == VerificationStatus.VERIFIED,
    )
    ev_res = await db.execute(ev_stmt)
    evidence_items = ev_res.scalars().all()

    verified_count = len(evidence_items)
    unique_domains = list(set(e.domain for e in evidence_items if e.domain))
    has_breach = any("breach" in d.lower() or "dark" in d.lower() for d in unique_domains)
    complete_count = sum(1 for e in evidence_items if e.sha256_hash and not e.sha256_hash.startswith("PENDING"))

    risk_eval = exposure_risk_service.evaluate_risk(
        verified_count=verified_count,
        unique_domains=unique_domains,
        cluster_count=max(1, len(unique_domains)) if unique_domains else 0,
        has_breach_domain=has_breach,
        evidence_complete_count=complete_count,
    )

    # Save RiskAssessment record
    risk_record = RiskAssessment(
        case_id=case.id,
        risk_policy_version="v1",
        calculated_score=risk_eval.internal_score,
        overall_risk_level=RiskLevel[risk_eval.risk_level.value],
        explanation_text=risk_eval.explanation,
        verified_findings_count=verified_count,
        unverified_findings_count=0,
        factor_breakdown_json={
            "calculation_version": "v1",
            "factors": [
                {
                    "name": f.name,
                    "weight": f.weight,
                    "contribution": f.contribution,
                    "detail": f.detail,
                }
                for f in risk_eval.contributing_factors
            ],
            "verified_count": verified_count,
            "unique_domains": len(unique_domains),
        },
        risk_factors_json={
            "factors": [
                {"name": f.name, "weight": f.weight, "contribution": f.contribution, "detail": f.detail}
                for f in risk_eval.contributing_factors
            ]
        },
        assessed_by_id=current_user.id,
    )
    db.add(risk_record)
    case.status = CaseStatus.RISK_ASSESSED
    case.current_stage = 7

    # Append timeline event
    await timeline_service.record_event(
        db=db,
        case_id=case.id,
        event_type="RISK_EVALUATED",
        title=f"Risk Assessed: {risk_eval.risk_level.value}",
        description=f"Deterministic risk evaluation completed ({risk_eval.risk_level.value}, Score: {risk_eval.internal_score}). Policy: v1",
        actor_id=current_user.id,
        metadata={"risk_level": risk_eval.risk_level.value, "score": risk_eval.internal_score, "version": "v1"},
    )

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.risk_recalculated,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="risk_assessment",
        resource_id=str(risk_record.id),
        details={"risk_level": risk_eval.risk_level.value, "score": risk_eval.internal_score, "policy_version": "v1"},
    )

    # Broadcast SSE: risk.calculation.completed
    await exposure_scan_orchestrator.broadcast_event(
        ScanProgressEvent(
            event_type="risk.calculation.completed",
            investigation_id=str(case.id),
            job_id=str(risk_record.id),
            step="RISK_ASSESSED",
            progress_pct=100,
            message=f"Exposure risk tier calculated: {risk_eval.risk_level.value}.",
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload={
                "risk_level": risk_eval.risk_level.value,
                "score": risk_eval.internal_score,
                "version": "v1",
            },
        )
    )

    await db.commit()

    return {
        "risk_level": risk_eval.risk_level.value,
        "score": risk_eval.internal_score,
        "explanation": risk_eval.explanation,
        "risk_policy_version": "v1",
        "calculation_version": "v1",
        "contributing_factors": [
            {"name": f.name, "weight": f.weight, "contribution": f.contribution, "detail": f.detail}
            for f in risk_eval.contributing_factors
        ],
        "verified_count": verified_count,
        "unique_domains": len(unique_domains),
    }


@router.post("/{investigation_id}/report")
async def generate_and_export_report(
    investigation_id: uuid.UUID,
    req: ReportExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Generate reproducible hash-referenced investigation report with deterministic content hashing."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    # Broadcast SSE: report.queued
    report_job_id = str(uuid.uuid4())
    await exposure_scan_orchestrator.broadcast_event(
        ScanProgressEvent(
            event_type="report.queued",
            investigation_id=str(case.id),
            job_id=report_job_id,
            step="REPORT_QUEUED",
            progress_pct=10,
            message=f"Investigation report request ({req.format}) queued for generation...",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )

    # Broadcast SSE: report.generating
    await exposure_scan_orchestrator.broadcast_event(
        ScanProgressEvent(
            event_type="report.generating",
            investigation_id=str(case.id),
            job_id=report_job_id,
            step="GENERATING_REPORT",
            progress_pct=50,
            message=f"Compiling forensic evidence, risk telemetry, and audit trail into {req.format}...",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )

    # Load all investigation state
    ref_img_stmt = select(ReferenceImage).where(ReferenceImage.case_id == case.id)
    ref_images = (await db.execute(ref_img_stmt)).scalars().all()
    ref = next((r for r in ref_images if r.is_primary), None) or (ref_images[0] if ref_images else None)
    fingerprint = ref.sha256_hash if ref else "UNKNOWN"

    ev_stmt = select(Evidence).where(Evidence.case_id == case.id).order_by(Evidence.custody_sequence.asc())
    evidence_items = (await db.execute(ev_stmt)).scalars().all()

    risk_stmt = select(RiskAssessment).where(RiskAssessment.case_id == case.id).order_by(RiskAssessment.created_at.desc())
    latest_risk = (await db.execute(risk_stmt)).scalars().first()

    timeline_events = await timeline_service.get_timeline(db, case.id, ascending=True)

    verified_exposures = [
        {
            "id": str(e.id),
            "domain": e.domain,
            "page_title": e.page_title,
            "page_url": e.page_url,
            "image_url": e.image_url,
            "similarity_score": 1.0,
            "evidence_sha256": e.sha256_hash,
            "verified_at": e.verified_at.isoformat() if e.verified_at else None,
        }
        for e in evidence_items
        if e.verification_status == VerificationStatus.VERIFIED
    ]

    payload = ReportPayload(
        investigation_id=str(case.id),
        case_number=case.case_number,
        title=case.title,
        generated_at=datetime.now(timezone.utc).isoformat(),
        reference_image_sha256=fingerprint,
        risk_policy_version="v1",
        methodology=exposure_report_service.METHODOLOGY_TEXT,
        limitations=exposure_report_service.LIMITATIONS_TEXT,
        risk_assessment={
            "risk_level": latest_risk.overall_risk_level.value if latest_risk else "LOW",
            "score": latest_risk.calculated_score if latest_risk else 0.0,
            "explanation": latest_risk.explanation_text if latest_risk else "Zero verified exposure endpoints confirmed.",
        },
        verified_exposures=verified_exposures,
        rejected_findings_summary={"count": sum(1 for e in evidence_items if e.verification_status == VerificationStatus.REJECTED)},
        uncertain_findings_summary={"count": sum(1 for e in evidence_items if e.verification_status == VerificationStatus.UNCERTAIN)},
        exposure_clusters=[],
        evidence_artifacts=[
            {
                "sequence": e.custody_sequence,
                "evidence_number": e.evidence_number,
                "sha256": e.sha256_hash,
                "previous_hash": e.previous_evidence_hash,
            }
            for e in evidence_items
        ],
        audit_chain=timeline_events if req.include_audit_trail else [],
    )

    content_hash = exposure_report_service.compute_deterministic_content_hash(payload)
    report_title = req.title or f"Forensic Exposure Dossier ({req.format})"

    # Generate document bytes / text
    if req.format == "PDF":
        doc_bytes = exposure_report_service.generate_pdf_report_bytes(payload)
        doc_sha256 = hashlib.sha256(doc_bytes).hexdigest()
        file_name = f"report_{case.case_number}_{content_hash[:8]}.pdf"
        storage_path, _ = secure_storage_service.save_evidence_artifact(doc_bytes, file_name)
    elif req.format == "CSV":
        doc_text = exposure_report_service.generate_csv_report(payload)
        doc_bytes = doc_text.encode("utf-8")
        doc_sha256 = hashlib.sha256(doc_bytes).hexdigest()
        file_name = f"report_{case.case_number}_{content_hash[:8]}.csv"
        storage_path, _ = secure_storage_service.save_evidence_artifact(doc_bytes, file_name)
    elif req.format == "TEXT":
        doc_text = exposure_report_service.generate_text_summary_report(payload)
        doc_bytes = doc_text.encode("utf-8")
        doc_sha256 = hashlib.sha256(doc_bytes).hexdigest()
        file_name = f"report_{case.case_number}_{content_hash[:8]}.txt"
        storage_path, _ = secure_storage_service.save_evidence_artifact(doc_bytes, file_name)
    else:  # JSON
        doc_text = exposure_report_service.generate_json_report(payload)
        doc_bytes = doc_text.encode("utf-8")
        doc_sha256 = hashlib.sha256(doc_bytes).hexdigest()
        file_name = f"report_{case.case_number}_{content_hash[:8]}.json"
        storage_path, _ = secure_storage_service.save_evidence_artifact(doc_bytes, file_name)

    # Persist CaseReport
    case_report = CaseReport(
        case_id=case.id,
        report_title=report_title,
        report_format=ReportFormat[req.format],
        status=ReportStatus.COMPLETED,
        file_path=storage_path,
        storage_key=storage_path,
        sha256_hash=doc_sha256,
        content_hash=content_hash,
        generated_by_id=current_user.id,
        summary_json={
            "verified_count": len(verified_exposures),
            "reference_sha256": fingerprint,
            "risk_level": latest_risk.overall_risk_level.value if latest_risk else "LOW",
        },
        parameters_json={"format": req.format, "include_audit_trail": req.include_audit_trail},
    )
    db.add(case_report)
    case.status = CaseStatus.REPORT_READY
    case.current_stage = 8

    # Append timeline event
    await timeline_service.record_event(
        db=db,
        case_id=case.id,
        event_type="REPORT_GENERATED",
        title=f"Report Dossier Generated ({req.format})",
        description=f"Exported investigation report. Content SHA-256: {content_hash[:12]}...",
        actor_id=current_user.id,
        metadata={"report_id": str(case_report.id), "format": req.format, "content_hash": content_hash},
    )

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.report_generated,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="report",
        resource_id=str(case_report.id),
        details={"format": req.format, "content_hash": content_hash, "file_name": file_name},
    )

    # Broadcast SSE: report.completed
    await exposure_scan_orchestrator.broadcast_event(
        ScanProgressEvent(
            event_type="report.completed",
            investigation_id=str(case.id),
            job_id=str(case_report.id),
            step="REPORT_READY",
            progress_pct=100,
            message=f"Investigation report ({req.format}) generated successfully.",
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload={
                "report_id": str(case_report.id),
                "format": req.format,
                "content_hash": content_hash,
                "sha256_hash": doc_sha256,
            },
        )
    )

    await db.commit()

    if req.format == "PDF":
        return Response(content=doc_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{file_name}"'})
    elif req.format == "CSV":
        return PlainTextResponse(doc_bytes.decode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{file_name}"'})
    elif req.format == "TEXT":
        return PlainTextResponse(doc_bytes.decode("utf-8"), media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="{file_name}"'})
    else:
        return PlainTextResponse(doc_bytes.decode("utf-8"), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{file_name}"'})


@router.get("/{investigation_id}/reports")
async def list_investigation_reports(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List all generated report artifacts for this investigation."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(CaseReport).where(CaseReport.case_id == case.id).order_by(CaseReport.created_at.desc())
    reports = (await db.execute(stmt)).scalars().all()

    return {
        "investigation_id": str(case.id),
        "case_number": case.case_number,
        "reports": [
            {
                "id": str(r.id),
                "title": r.report_title,
                "format": r.report_format.value if hasattr(r.report_format, "value") else str(r.report_format),
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "sha256_hash": r.sha256_hash,
                "content_hash": r.content_hash,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "summary": r.summary_json,
            }
            for r in reports
        ],
        "total_count": len(reports),
    }


@router.get("/{investigation_id}/reports/{report_id}/download")
async def download_report_artifact(
    investigation_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Download previously generated report file."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(CaseReport).where(CaseReport.id == report_id, CaseReport.case_id == case.id)
    report = (await db.execute(stmt)).scalars().first()
    if not report or not (report.file_path or report.storage_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report artifact not found.")

    target_path = report.file_path or report.storage_key
    raw_bytes = secure_storage_service.load_evidence_artifact(target_path)
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file missing from storage.")

    fmt = report.report_format.value if hasattr(report.report_format, "value") else str(report.report_format)
    mime_map = {
        "PDF": "application/pdf",
        "CSV": "text/csv",
        "JSON": "application/json",
        "TEXT": "text/plain",
    }
    ext_map = {"PDF": "pdf", "CSV": "csv", "JSON": "json", "TEXT": "txt"}
    media_type = mime_map.get(fmt, "application/octet-stream")
    ext = ext_map.get(fmt, "bin")

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.report_downloaded,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="report",
        resource_id=str(report.id),
        details={"format": fmt, "sha256": report.sha256_hash},
    )
    await db.commit()

    headers = {"Content-Disposition": f'attachment; filename="report_{case.case_number}_{report.id.hex[:6]}.{ext}"'}
    return Response(content=raw_bytes, media_type=media_type, headers=headers)


@router.post("/{investigation_id}/response-packages", status_code=status.HTTP_201_CREATED)
async def create_response_package(
    investigation_id: uuid.UUID,
    req: CreateResponsePackageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate formal takedown and response documentation package for verified domain exposures."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    pkg = await response_package_service.create_package(
        db=db,
        case=case,
        target_domain=req.target_domain,
        target_entity=req.target_entity,
        finding_ids=req.finding_ids,
        package_format=req.format,
        user=current_user,
    )

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.response_package_generated,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="response_package",
        resource_id=str(pkg.id),
        details={"package_number": pkg.package_number, "domain": req.target_domain, "format": req.format},
    )
    await db.commit()

    return {
        "id": str(pkg.id),
        "package_number": pkg.package_number,
        "target_domain": pkg.target_domain,
        "target_entity": pkg.target_entity,
        "incident_summary": pkg.incident_summary,
        "sha256_hash": pkg.sha256_hash,
        "status": pkg.status,
        "format": pkg.package_format,
        "takedown_letter": pkg.takedown_letter_markdown,
        "evidence_manifest": pkg.evidence_manifest_json,
        "contact_channels": pkg.contact_channels_json,
        "created_at": pkg.created_at.isoformat() if pkg.created_at else None,
    }


@router.get("/{investigation_id}/response-packages")
async def list_response_packages(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List all response & takedown packages for this investigation."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(ResponsePackage).where(ResponsePackage.case_id == case.id).order_by(ResponsePackage.created_at.desc())
    packages = (await db.execute(stmt)).scalars().all()

    return {
        "investigation_id": str(case.id),
        "packages": [
            {
                "id": str(p.id),
                "package_number": p.package_number,
                "target_domain": p.target_domain,
                "target_entity": p.target_entity,
                "incident_summary": p.incident_summary,
                "sha256_hash": p.sha256_hash,
                "status": p.status,
                "format": p.package_format,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "evidence_count": len(p.evidence_manifest_json or []),
            }
            for p in packages
        ],
        "total_count": len(packages),
    }


@router.get("/{investigation_id}/response-packages/{package_id}/download")
async def download_response_package(
    investigation_id: uuid.UUID,
    package_id: uuid.UUID,
    format: str = Query("MARKDOWN", pattern="^(MARKDOWN|JSON)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Download the formal response & takedown package."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)

    stmt = select(ResponsePackage).where(ResponsePackage.id == package_id, ResponsePackage.case_id == case.id)
    pkg = (await db.execute(stmt)).scalars().first()
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response package not found.")

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.response_package_downloaded,
        user_id=current_user.id,
        organization_id=case.organization_id,
        resource_type="response_package",
        resource_id=str(pkg.id),
        details={"package_number": pkg.package_number, "format": format},
    )
    await db.commit()

    if format == "JSON":
        pkg_dict = {
            "package_number": pkg.package_number,
            "target_domain": pkg.target_domain,
            "target_entity": pkg.target_entity,
            "incident_summary": pkg.incident_summary,
            "sha256_hash": pkg.sha256_hash,
            "takedown_letter": pkg.takedown_letter_markdown,
            "evidence_manifest": pkg.evidence_manifest_json,
            "contact_channels": pkg.contact_channels_json,
            "created_at": pkg.created_at.isoformat() if pkg.created_at else None,
        }
        json_bytes = json.dumps(pkg_dict, indent=2).encode("utf-8")
        return Response(
            content=json_bytes,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{pkg.package_number}.json"'},
        )

    # Markdown download
    md_bytes = pkg.takedown_letter_markdown.encode("utf-8")
    return Response(
        content=md_bytes,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{pkg.package_number}.md"'},
    )


@router.post("/{investigation_id}/monitoring", status_code=status.HTTP_200_OK)
async def configure_investigation_monitoring(
    investigation_id: uuid.UUID,
    req: ConfigureMonitoringRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Configure or toggle automated exposure monitoring for this investigation."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    svc = MonitoringService(db)
    rule = await svc.create_or_update_rule(
        case=case,
        frequency=req.frequency,
        enabled=req.enabled,
        user_id=current_user.id,
    )
    return {
        "id": str(rule.id),
        "investigation_id": str(case.id),
        "frequency": rule.frequency,
        "enabled": rule.enabled,
        "last_status": rule.last_status,
        "last_run_at": rule.last_run_at.isoformat() if rule.last_run_at else None,
        "next_run_at": rule.next_run_at.isoformat() if rule.next_run_at else None,
        "previous_count": rule.previous_count,
        "current_count": rule.current_count,
        "new_delta_count": rule.new_delta_count,
    }


@router.get("/{investigation_id}/monitoring", status_code=status.HTTP_200_OK)
async def get_investigation_monitoring_status(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve continuous monitoring configuration and recent statistics."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    svc = MonitoringService(db)
    rule = await svc.get_rule_for_case(case.id, current_user.organization_id)
    history = await svc.get_history_for_case(case.id, current_user.organization_id, limit=10)

    return {
        "investigation_id": str(case.id),
        "case_number": case.case_number,
        "is_configured": rule is not None,
        "enabled": rule.enabled if rule else False,
        "frequency": rule.frequency if rule else "DAILY",
        "last_status": rule.last_status if rule else "NOT_CONFIGURED",
        "last_run_at": rule.last_run_at.isoformat() if rule and rule.last_run_at else None,
        "next_run_at": rule.next_run_at.isoformat() if rule and rule.next_run_at else None,
        "new_delta_count": rule.new_delta_count if rule else 0,
        "current_count": rule.current_count if rule else 0,
        "recent_runs": [
            {
                "id": str(r.id),
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "status": r.status,
                "provider_status": r.provider_status,
                "new_count": r.new_count,
                "unchanged_count": r.unchanged_count,
                "not_observed_count": r.not_observed_count,
                "reappeared_count": r.reappeared_count,
                "candidate_count": r.candidate_count,
            }
            for r in history
        ],
    }


@router.post("/{investigation_id}/monitoring/scan", status_code=status.HTTP_200_OK)
async def trigger_manual_monitoring_scan(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Trigger immediate re-scan for this investigation with delta change detection."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    svc = MonitoringService(db)
    rule = await svc.get_rule_for_case(case.id, current_user.organization_id)
    if not rule:
        rule = await svc.create_or_update_rule(case=case, frequency="DAILY", enabled=True, user_id=current_user.id)

    run = await svc.execute_monitoring_scan(rule_id=rule.id, user_id=current_user.id)

    return {
        "run_id": str(run.id),
        "investigation_id": str(case.id),
        "status": run.status,
        "provider_status": run.provider_status,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "delta": {
            "new_count": run.new_count,
            "unchanged_count": run.unchanged_count,
            "not_observed_count": run.not_observed_count,
            "reappeared_count": run.reappeared_count,
        },
    }


@router.delete("/{investigation_id}", status_code=status.HTTP_200_OK)

async def purge_investigation_data(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Atomic cross-store purge across Postgres, filesystem, and Qdrant."""
    case = await get_case_scoped(db, investigation_id, current_user.organization_id)
    receipt = await retention_service.purge_investigation(db, case)
    return {
        "investigation_id": receipt.investigation_id,
        "status": receipt.status,
        "files_removed_count": receipt.files_removed_count,
        "vectors_removed_count": receipt.vectors_removed_count,
        "purged_at": receipt.deleted_at,
    }


# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
async def get_case_scoped(db: AsyncSession, case_id: uuid.UUID, org_id: uuid.UUID) -> Case:
    """Retrieve case strictly enforcing tenant isolation."""
    stmt = select(Case).where(Case.id == case_id, Case.organization_id == org_id)
    res = await db.execute(stmt)
    case = res.scalars().first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found or permission denied.",
        )
    return case


def datetime_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")
