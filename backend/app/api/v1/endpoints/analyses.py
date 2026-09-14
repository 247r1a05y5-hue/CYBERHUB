"""Analyses API endpoints."""
from __future__ import annotations

import json
import math
from typing import List, Optional
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.analysis import AnalysisStatus
from app.models.analysis_input import InputType
from app.models.user import User
from app.repositories.analysis import AnalysisRepository
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisSubmissionRequest,
    AnalysisSummary,
)
from app.schemas.common import PaginatedResponse
from app.services.analysis_orchestrator import AnalysisOrchestrator

router = APIRouter()


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit item for asynchronous analysis",
)
async def submit_analysis(
    req: Optional[AnalysisSubmissionRequest] = None,
    file: Optional[UploadFile] = File(None),
    analyzer_type: str = Form(None),
    input_type: str = Form(None),
    payload: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    orchestrator = AnalysisOrchestrator(session)
    file_bytes: Optional[bytes] = None
    original_filename: Optional[str] = None

    if file:
        file_bytes = await file.read()
        original_filename = file.filename
        inp_t = InputType.file
        submission = AnalysisSubmissionRequest(
            analyzer_type=analyzer_type or "mock",
            input_type=inp_t,
            payload=payload,
        )
    elif req:
        submission = req
    else:
        inp_t = InputType(input_type) if input_type in InputType.__members__ else InputType.text
        submission = AnalysisSubmissionRequest(
            analyzer_type=analyzer_type or "mock",
            input_type=inp_t,
            payload=payload,
        )

    analysis = await orchestrator.submit_analysis(
        organization_id=current_user.organization_id,
        request=submission,
        file_bytes=file_bytes,
        original_filename=original_filename,
        actor_id=current_user.id,
    )
    return AnalysisResponse.model_validate(analysis)


@router.get(
    "",
    response_model=PaginatedResponse[AnalysisResponse],
    summary="List analyses with pagination and filtering",
)
async def list_analyses(
    status: Optional[AnalysisStatus] = None,
    analyzer_type: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AnalysisResponse]:
    repo = AnalysisRepository(session)
    offset = (page - 1) * size
    items, total = await repo.list_by_org(
        organization_id=current_user.organization_id,
        status=status,
        analyzer_type=analyzer_type,
        limit=size,
        offset=offset,
    )
    pages = math.ceil(total / size) if total > 0 else 1

    return PaginatedResponse(
        items=[AnalysisResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get analysis by ID with complete results",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    repo = AnalysisRepository(session)
    analysis = await repo.get_with_details(analysis_id, current_user.organization_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )
    return AnalysisResponse.model_validate(analysis)
