"""Evidence API endpoints."""
from __future__ import annotations

import math
from typing import Optional
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_role
from app.models.evidence import EvidenceType
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.services.evidence import EvidenceService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[EvidenceResponse],
    summary="List evidence artifacts with pagination",
)
async def list_evidence(
    analysis_id: Optional[uuid.UUID] = None,
    incident_id: Optional[uuid.UUID] = None,
    evidence_type: Optional[EvidenceType] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[EvidenceResponse]:
    service = EvidenceService(session)
    offset = (page - 1) * size
    items, total = await service.list_evidence(
        organization_id=current_user.organization_id,
        analysis_id=analysis_id,
        incident_id=incident_id,
        evidence_type=evidence_type,
        limit=size,
        offset=offset,
    )
    pages = math.ceil(total / size) if total > 0 else 1

    return PaginatedResponse(
        items=[EvidenceResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or record an evidence artifact",
)
async def create_evidence(
    req: Optional[EvidenceCreate] = None,
    file: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    evidence_type: Optional[str] = Form(None),
    analysis_id: Optional[str] = Form(None),
    incident_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    service = EvidenceService(session)
    file_bytes: Optional[bytes] = None

    if file:
        file_bytes = await file.read()
        evidence_in = EvidenceCreate(
            title=title or file.filename or "Uploaded Artifact",
            evidence_type=EvidenceType(evidence_type) if evidence_type in EvidenceType.__members__ else EvidenceType.file,
            analysis_id=uuid.UUID(analysis_id) if analysis_id else None,
            incident_id=uuid.UUID(incident_id) if incident_id else None,
            description=description,
            original_filename=file.filename,
        )
    elif req:
        evidence_in = req
    else:
        evidence_in = EvidenceCreate(
            title=title or "Evidence Item",
            evidence_type=EvidenceType(evidence_type) if evidence_type in EvidenceType.__members__ else EvidenceType.text,
            analysis_id=uuid.UUID(analysis_id) if analysis_id else None,
            incident_id=uuid.UUID(incident_id) if incident_id else None,
            description=description,
        )

    evidence = await service.create_evidence(
        organization_id=current_user.organization_id,
        evidence_in=evidence_in,
        file_bytes=file_bytes,
        actor_id=current_user.id,
    )
    return EvidenceResponse.model_validate(evidence)


@router.get(
    "/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Get evidence metadata",
)
async def get_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    service = EvidenceService(session)
    evidence = await service.get_evidence(evidence_id, current_user.organization_id)
    return EvidenceResponse.model_validate(evidence)


@router.get(
    "/{evidence_id}/download",
    summary="Download evidence binary content",
)
async def download_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = EvidenceService(session)
    evidence = await service.get_evidence(evidence_id, current_user.organization_id)
    content = await service.get_evidence_bytes(evidence_id, current_user.organization_id)

    media_type = evidence.mime_type or "application/octet-stream"
    filename = evidence.original_filename or f"evidence_{evidence_id}.bin"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
