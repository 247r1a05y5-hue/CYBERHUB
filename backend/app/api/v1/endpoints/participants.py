"""Participant & Dataset Match API endpoints.

Privacy rule (enforced via response schemas):
  No response schema includes storage_key, raw image URL, or image bytes.
  Only participant_confirmed public source URLs are returned in match responses.

Tenant isolation: every query is scoped by organization_id from the JWT.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.participant import VerificationStatus
from app.models.user import User, UserRole
from app.services.participant_service import ParticipantService

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas — storage_key deliberately absent from all schemas
# ---------------------------------------------------------------------------


class ParticipantResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    participant_code: str
    display_name: str
    consent_status: str
    consent_timestamp: datetime | None = None
    is_active: bool
    notes: str | None = None

    class Config:
        from_attributes = True


class ParticipantImageResponse(BaseModel):
    """Image metadata — NEVER includes storage_key or image_url."""
    id: uuid.UUID
    participant_id: uuid.UUID
    mime_type: str
    file_size_bytes: int
    width: int | None = None
    height: int | None = None
    sha256: str
    phash: str | None = None
    dhash: str | None = None
    aws_face_id: str | None = None
    aws_external_image_id: str | None = None
    index_status: str
    index_error: str | None = None
    aws_indexed_at: datetime | None = None
    face_confidence: float | None = None
    image_sequence: int


class PublicSourceResponse(BaseModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    platform: str
    url: str
    participant_confirmed: bool


class PublicSourceEntry(BaseModel):
    platform: str
    url: str
    participant_confirmed: bool = True

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = {"instagram", "linkedin", "facebook", "twitter", "tiktok", "youtube", "other"}
        v = v.lower().strip()
        if v not in allowed:
            v = "other"
        return v


class DatasetStatsResponse(BaseModel):
    participant_count: int
    image_count: int
    indexed_face_count: int
    source_count: int
    consent_pending_count: int
    last_match_at: datetime | None = None
    aws_configured: bool


class MatchCandidateResponse(BaseModel):
    """Match result — NEVER includes participant image or storage key."""
    match_id: uuid.UUID
    participant_id: str
    participant_code: str
    display_name: str
    aws_similarity: float
    aws_face_id: str
    aws_external_image_id: str
    match_status: str
    matched_at: datetime
    public_sources: list[dict[str, str]]
    # Local secondary — clearly labeled, never blended with aws_similarity
    local_similarity: float | None = None
    local_match_method: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class VerificationRequest(BaseModel):
    status: str  # VERIFIED | REJECTED | UNCERTAIN
    verification_note: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {s.value for s in VerificationStatus}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class VerificationResponse(BaseModel):
    id: uuid.UUID
    match_id: uuid.UUID
    organization_id: uuid.UUID
    status: str
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None
    verification_note: str | None = None


# ---------------------------------------------------------------------------
# Participant CRUD
# ---------------------------------------------------------------------------


@router.get("/participants", response_model=list[ParticipantResponse])
async def list_participants(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ParticipantResponse]:
    """List all active participants for the authenticated user's organization."""
    svc = ParticipantService(session)
    participants = await svc.list_participants(current_user.organization_id)
    return [
        ParticipantResponse(
            id=p.id,
            organization_id=p.organization_id,
            participant_code=p.participant_code,
            display_name=p.display_name,
            consent_status=p.consent_status.value,
            consent_timestamp=p.consent_timestamp,
            is_active=p.is_active,
            notes=p.notes,
        )
        for p in participants
    ]


@router.post("/participants", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
async def create_participant(
    display_name: str = Form(...),
    participant_code: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    grant_consent: bool = Form(default=False, description="If true, immediately records consent"),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> ParticipantResponse:
    """Create a new participant (admin only). Optionally grant consent immediately."""
    svc = ParticipantService(session)
    try:
        participant = await svc.create_participant(
            organization_id=current_user.organization_id,
            display_name=display_name.strip(),
            participant_code=participant_code.strip() if participant_code else None,
            notes=notes,
            actor_id=current_user.id,
        )
        if grant_consent:
            participant = await svc.grant_consent(
                participant_id=participant.id,
                organization_id=current_user.organization_id,
                method="ADMIN_ENROLLMENT",
                actor_id=current_user.id,
            )
        await session.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ParticipantResponse(
        id=participant.id,
        organization_id=participant.organization_id,
        participant_code=participant.participant_code,
        display_name=participant.display_name,
        consent_status=participant.consent_status.value,
        consent_timestamp=participant.consent_timestamp,
        is_active=participant.is_active,
        notes=participant.notes,
    )


@router.get("/participants/{participant_id}", response_model=ParticipantResponse)
async def get_participant(
    participant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ParticipantResponse:
    svc = ParticipantService(session)
    participant = await svc.get_participant(participant_id, current_user.organization_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return ParticipantResponse(
        id=participant.id,
        organization_id=participant.organization_id,
        participant_code=participant.participant_code,
        display_name=participant.display_name,
        consent_status=participant.consent_status.value,
        consent_timestamp=participant.consent_timestamp,
        is_active=participant.is_active,
        notes=participant.notes,
    )


@router.delete("/participants/{participant_id}", status_code=status.HTTP_200_OK)
async def delete_participant(
    participant_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a participant and all their data (DB, storage, AWS FaceIds)."""
    svc = ParticipantService(session)
    try:
        report = await svc.delete_participant(
            participant_id=participant_id,
            organization_id=current_user.organization_id,
            actor_id=current_user.id,
        )
        await session.commit()
        return {"deleted": True, "report": report}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------


@router.post(
    "/participants/{participant_id}/images",
    response_model=ParticipantImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_participant_image(
    participant_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> ParticipantImageResponse:
    """Upload and validate a participant image. Checks size, MIME, magic bytes,
    Pillow decode, dimensions, decompression bomb, single face.
    Returns image metadata — never returns storage_key or image URL.
    """
    data = await file.read()
    svc = ParticipantService(session)
    try:
        detail = await svc.add_participant_image(
            participant_id=participant_id,
            organization_id=current_user.organization_id,
            image_data=data,
            original_filename=file.filename or "upload.jpg",
            actor_id=current_user.id,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return ParticipantImageResponse(
        id=detail.id,
        participant_id=detail.participant_id,
        mime_type=detail.mime_type,
        file_size_bytes=detail.file_size_bytes,
        width=detail.width,
        height=detail.height,
        sha256=detail.sha256,
        phash=detail.phash,
        dhash=detail.dhash,
        aws_face_id=detail.aws_face_id,
        aws_external_image_id=detail.aws_external_image_id,
        index_status=detail.index_status,
        index_error=detail.index_error,
        aws_indexed_at=detail.aws_indexed_at,
        face_confidence=detail.face_confidence,
        image_sequence=detail.image_sequence,
    )


# ---------------------------------------------------------------------------
# Public source management
# ---------------------------------------------------------------------------


@router.post(
    "/participants/{participant_id}/sources",
    response_model=PublicSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_public_source(
    participant_id: uuid.UUID,
    source: PublicSourceEntry,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> PublicSourceResponse:
    """Add a participant-confirmed public URL."""
    svc = ParticipantService(session)
    try:
        src = await svc.add_public_source(
            participant_id=participant_id,
            organization_id=current_user.organization_id,
            platform=source.platform,
            url=source.url,
            participant_confirmed=source.participant_confirmed,
            actor_id=current_user.id,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return PublicSourceResponse(
        id=src.id,
        participant_id=src.participant_id,
        platform=src.platform,
        url=src.url,
        participant_confirmed=src.participant_confirmed,
    )


# ---------------------------------------------------------------------------
# AWS Indexing
# ---------------------------------------------------------------------------


@router.post(
    "/participants/{participant_id}/index",
    response_model=list[ParticipantImageResponse],
)
async def index_participant(
    participant_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> list[ParticipantImageResponse]:
    """Index all pending images into AWS Rekognition.
    Participant must have CONSENTED consent_status.
    """
    svc = ParticipantService(session)
    try:
        details = await svc.index_participant_images(
            participant_id=participant_id,
            organization_id=current_user.organization_id,
            actor_id=current_user.id,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return [
        ParticipantImageResponse(
            id=d.id,
            participant_id=d.participant_id,
            mime_type=d.mime_type,
            file_size_bytes=d.file_size_bytes,
            width=d.width,
            height=d.height,
            sha256=d.sha256,
            phash=d.phash,
            dhash=d.dhash,
            aws_face_id=d.aws_face_id,
            aws_external_image_id=d.aws_external_image_id,
            index_status=d.index_status,
            index_error=d.index_error,
            aws_indexed_at=d.aws_indexed_at,
            face_confidence=d.face_confidence,
            image_sequence=d.image_sequence,
        )
        for d in details
    ]


# ---------------------------------------------------------------------------
# Camera Match
# ---------------------------------------------------------------------------


@router.post("/match", response_model=MatchCandidateResponse)
async def dataset_match(
    file: UploadFile = File(...),
    case_id: str | None = Form(default=None),
    face_match_threshold: float = Form(default=80.0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MatchCandidateResponse:
    """Search the controlled dataset by face.

    Validates the query image, runs SearchFacesByImage via AWS Rekognition,
    maps FaceId → Participant, and returns participant metadata + confirmed
    public URLs. NEVER returns the participant's stored photograph.

    Error codes:
      AWS_NOT_CONFIGURED, AWS_AUTH_FAILED, AWS_ACCESS_DENIED,
      AWS_COLLECTION_NOT_FOUND, AWS_INVALID_IMAGE, AWS_THROTTLED,
      AWS_SERVICE_UNAVAILABLE, NO_FACE_DETECTED, MULTIPLE_FACES_DETECTED,
      NO_DATASET_MATCH
    """
    data = await file.read()
    case_uuid: uuid.UUID | None = None
    if case_id:
        try:
            case_uuid = uuid.UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case_id UUID")

    svc = ParticipantService(session)
    candidate = await svc.match_face(
        organization_id=current_user.organization_id,
        image_data=data,
        case_id=case_uuid,
        actor_id=current_user.id,
        face_match_threshold=face_match_threshold,
    )
    await session.commit()

    return MatchCandidateResponse(
        match_id=candidate.match_id,
        participant_id=str(candidate.participant_id),
        participant_code=candidate.participant_code,
        display_name=candidate.display_name,
        aws_similarity=candidate.aws_similarity,
        aws_face_id=candidate.aws_face_id,
        aws_external_image_id=candidate.aws_external_image_id,
        match_status=candidate.match_status,
        matched_at=candidate.matched_at,
        public_sources=candidate.public_sources,
        local_similarity=candidate.local_similarity,
        local_match_method=candidate.local_match_method,
        error_code=candidate.error_code,
        error_message=candidate.error_message,
    )


# ---------------------------------------------------------------------------
# Human verification
# ---------------------------------------------------------------------------


@router.post("/matches/{match_id}/verify", response_model=VerificationResponse)
async def verify_match(
    match_id: uuid.UUID,
    req: VerificationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VerificationResponse:
    """Record a human verification decision on a match."""
    svc = ParticipantService(session)
    try:
        verification = await svc.verify_match(
            match_id=match_id,
            organization_id=current_user.organization_id,
            status=VerificationStatus(req.status),
            verification_note=req.verification_note,
            actor_id=current_user.id,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return VerificationResponse(
        id=verification.id,
        match_id=verification.match_id,
        organization_id=verification.organization_id,
        status=verification.status.value,
        verified_by=verification.verified_by,
        verified_at=verification.verified_at,
        verification_note=verification.verification_note,
    )


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=DatasetStatsResponse)
async def get_dataset_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DatasetStatsResponse:
    """Dataset dashboard statistics — participant count, image count, etc."""
    from app.services.aws_rekognition_service import rekognition_service

    svc = ParticipantService(session)
    stats = await svc.get_stats(current_user.organization_id)
    return DatasetStatsResponse(
        participant_count=stats.participant_count,
        image_count=stats.image_count,
        indexed_face_count=stats.indexed_face_count,
        source_count=stats.source_count,
        consent_pending_count=stats.consent_pending_count,
        last_match_at=stats.last_match_at,
        aws_configured=rekognition_service.is_configured,
    )


class IngestionRequest(BaseModel):
    dataset_dir: str = "CYBERHUB_CONTROLLED_DATASET"
    auto_index_aws: bool = False


class IngestionResponse(BaseModel):
    organization_id: uuid.UUID
    dataset_dir: str
    participants_created: int
    participants_skipped: int
    consents_recorded: int
    images_ingested: int
    images_skipped: int
    images_indexed_aws: int
    sources_ingested: int
    sources_skipped: int
    errors: list[str]
    success: bool


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_controlled_dataset(
    req: IngestionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """Ingest a CYBERHUB_CONTROLLED_DATASET folder into PostgreSQL with full validation."""
    from app.services.dataset_ingestion_service import ControlledDatasetIngestionService

    svc = ControlledDatasetIngestionService(session)
    report = await svc.ingest_dataset_directory(
        dataset_dir=req.dataset_dir,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        auto_index_aws=req.auto_index_aws,
    )
    await session.commit()

    return IngestionResponse(
        organization_id=report.organization_id,
        dataset_dir=report.dataset_dir,
        participants_created=report.participants_created,
        participants_skipped=report.participants_skipped,
        consents_recorded=report.consents_recorded,
        images_ingested=report.images_ingested,
        images_skipped=report.images_skipped,
        images_indexed_aws=report.images_indexed_aws,
        sources_ingested=report.sources_ingested,
        sources_skipped=report.sources_skipped,
        errors=report.errors,
        success=report.is_success,
    )
