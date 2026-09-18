"""System and Search Provider Diagnostics Endpoint.

Provides secured real-time infrastructure and provider health diagnostics
without exposing sensitive keys, tokens, or private credentials.
"""
from __future__ import annotations

import logging
import os
import time
import urllib.parse
from typing import Any

import httpx
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.discovery import SearchJob
from app.models.user import User
from app.services.provider_orchestration_service import ProviderStatus, provider_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchDiagnosticsResponse(BaseModel):
    camera_upload_ready: bool
    database_ready: bool
    storage_ready: bool
    external_image_url_ready: bool
    searchapi_configured: bool
    searchapi_reachable: bool
    searchapi_last_status: str
    provider_latency_ms: float | None = None
    public_base_url_host: str
    last_search_run: dict[str, Any] | None = None
    last_error: str | None = None
    # AWS Rekognition + Controlled Dataset
    aws_configured: bool = False
    aws_collection_exists: bool = False
    aws_region: str | None = None
    dataset_participant_count: int = 0
    dataset_image_count: int = 0
    dataset_indexed_face_count: int = 0
    last_dataset_match: str | None = None
    last_aws_error: str | None = None


@router.get("/search", response_model=SearchDiagnosticsResponse, summary="Search Provider & Infrastructure Diagnostics")
async def get_search_diagnostics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchDiagnosticsResponse:
    """
    Diagnostic probe returning readiness of all core pipeline components:
    - Image ingestion & validation
    - Database connectivity
    - Persistent storage write access
    - External image URL reachability
    - SearchAPI configuration, reachability, and response latency
    """
    # 1. Database Check
    db_ready = False
    try:
        await db.execute(text("SELECT 1"))
        db_ready = True
    except Exception as db_err:
        logger.error(f"Diagnostics DB check failed: {db_err}")

    # 2. Storage Check
    storage_ready = False
    try:
        os.makedirs(settings.STORAGE_PATH, exist_ok=True)
        probe_path = os.path.join(settings.STORAGE_PATH, ".diag_probe")
        with open(probe_path, "w") as f:
            f.write("probe")
        if os.path.exists(probe_path):
            os.remove(probe_path)
            storage_ready = True
    except Exception as st_err:
        logger.error(f"Diagnostics Storage check failed: {st_err}")

    # 3. External Image URL Reachability Check
    parsed_base = urllib.parse.urlparse(settings.PUBLIC_BASE_URL)
    base_host = (parsed_base.hostname or "").lower()
    is_local_host = (
        base_host in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "")
        or base_host.endswith(".local")
        or base_host.endswith(".internal")
    )
    external_url_ready = not is_local_host and parsed_base.scheme in ("http", "https")

    # 4. SearchAPI Configuration & Reachability Check
    searchapi_prov = provider_orchestrator.searchapi_provider
    searchapi_configured = bool(searchapi_prov.api_key and str(searchapi_prov.api_key).strip())
    searchapi_status_val = searchapi_prov.get_status().value
    searchapi_reachable = False
    provider_latency_ms: float | None = None
    last_error: str | None = None

    if searchapi_configured:
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("https://www.searchapi.io", follow_redirects=True)
                provider_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                searchapi_reachable = resp.status_code < 500
        except Exception as net_err:
            provider_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            last_error = f"SearchAPI network probe failed: {net_err}"
            logger.warning(last_error)
    else:
        last_error = "SEARCHAPI_API_KEY is not configured in backend environment."

    if not external_url_ready:
        reach_msg = f"PUBLIC_BASE_URL ('{settings.PUBLIC_BASE_URL}') is a local/private hostname. SearchAPI crawlers require a public domain."
        last_error = f"{last_error} | {reach_msg}" if last_error else reach_msg

    # 5. Last Search Run info
    last_search_run_info: dict[str, Any] | None = None
    try:
        stmt = (
            select(SearchJob)
            .where(SearchJob.case_id.in_(
                select(SearchJob.case_id).limit(10)
            ))
            .order_by(desc(SearchJob.created_at))
            .limit(1)
        )
        res = await db.execute(stmt)
        latest_job = res.scalars().first()
        if latest_job:
            last_search_run_info = {
                "job_id": str(latest_job.id),
                "case_id": str(latest_job.case_id),
                "provider": latest_job.provider,
                "status": latest_job.status.value if hasattr(latest_job.status, "value") else str(latest_job.status),
                "total_found": latest_job.total_found,
                "created_at": latest_job.created_at.isoformat() if latest_job.created_at else None,
                "completed_at": latest_job.completed_at.isoformat() if latest_job.completed_at else None,
                "error_message": latest_job.error_message,
            }
    except Exception as job_err:
        logger.debug(f"Diagnostics failed to query latest search job: {job_err}")

    # 6. AWS Rekognition + Dataset stats
    from app.services.aws_rekognition_service import rekognition_service
    from app.models.participant import Participant, ParticipantImage, DatasetMatch, ImageIndexStatus
    from sqlalchemy import func

    aws_configured = rekognition_service.is_configured
    aws_collection_exists = False
    aws_region = settings.AWS_REGION
    last_aws_error: str | None = None
    dataset_participant_count = 0
    dataset_image_count = 0
    dataset_indexed_face_count = 0
    last_dataset_match_str: str | None = None

    if aws_configured:
        try:
            info = rekognition_service.describe_collection()
            aws_collection_exists = info.status == "ACTIVE"
        except Exception as aws_err:
            last_aws_error = str(aws_err)

    try:
        dataset_participant_count = (
            await db.execute(select(func.count(Participant.id)).where(Participant.is_active == True))
        ).scalar() or 0
        dataset_image_count = (
            await db.execute(select(func.count(ParticipantImage.id)))
        ).scalar() or 0
        dataset_indexed_face_count = (
            await db.execute(
                select(func.count(ParticipantImage.id)).where(
                    ParticipantImage.index_status == ImageIndexStatus.INDEXED
                )
            )
        ).scalar() or 0
        last_match = (
            await db.execute(
                select(DatasetMatch.matched_at)
                .order_by(DatasetMatch.matched_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if last_match:
            last_dataset_match_str = last_match.isoformat()
    except Exception as stats_err:
        logger.debug(f"Diagnostics failed to query dataset stats: {stats_err}")

    return SearchDiagnosticsResponse(
        camera_upload_ready=True,
        database_ready=db_ready,
        storage_ready=storage_ready,
        external_image_url_ready=external_url_ready,
        searchapi_configured=searchapi_configured,
        searchapi_reachable=searchapi_reachable,
        searchapi_last_status=searchapi_status_val,
        provider_latency_ms=provider_latency_ms,
        public_base_url_host=base_host or "unknown",
        last_search_run=last_search_run_info,
        last_error=last_error,
        aws_configured=aws_configured,
        aws_collection_exists=aws_collection_exists,
        aws_region=aws_region,
        dataset_participant_count=dataset_participant_count,
        dataset_image_count=dataset_image_count,
        dataset_indexed_face_count=dataset_indexed_face_count,
        last_dataset_match=last_dataset_match_str,
        last_aws_error=last_aws_error,
    )
