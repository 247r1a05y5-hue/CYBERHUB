"""Dataset API endpoints — Bounded dataset management, admin enrollment, readiness reporting."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.dataset import Dataset, DatasetIdentity
from app.models.user import User, UserRole
from app.services.dataset_service import DatasetService

router = APIRouter()


class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    version: str
    category: str
    status: str
    is_active: bool


class DatasetEnrollRequest(BaseModel):
    identity_code: str
    full_name: str
    role_title: str | None = None
    department: str | None = None
    photo_url: str | None = None
    metadata: dict[str, Any] | None = None


class DatasetIdentityResponse(BaseModel):
    id: uuid.UUID
    identity_code: str
    full_name: str
    role_title: str | None = None
    department: str | None = None
    photo_url: str | None = None


class DatasetReadinessResponse(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    version: str
    total_records: int
    valid_records: int
    invalid_records: int
    indexed_identities: int
    embedding_status: str
    is_ready_for_matching: bool


@router.get("", response_model=list[DatasetResponse], summary="List authorized datasets")
async def list_datasets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[DatasetResponse]:
    dataset_service = DatasetService(session)
    dataset = await dataset_service.get_or_create_default_dataset(current_user.organization_id)
    await session.commit()

    return [
        DatasetResponse(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            version=dataset.version,
            category=dataset.category,
            status=dataset.status.value,
            is_active=dataset.is_active,
        )
    ]


@router.get("/{id}/identities", response_model=list[DatasetIdentityResponse], summary="List identities in dataset")
async def list_identities(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[DatasetIdentityResponse]:
    stmt = select(DatasetIdentity).where(DatasetIdentity.dataset_id == id)
    identities = list((await session.execute(stmt)).scalars().all())
    return [
        DatasetIdentityResponse(
            id=i.id,
            identity_code=i.identity_code,
            full_name=i.full_name,
            role_title=i.role_title,
            department=i.department,
            photo_url=i.photo_url,
        )
        for i in identities
    ]


@router.post(
    "/{id}/enroll",
    response_model=DatasetIdentityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll identity into authorized dataset (Admin only)",
)
async def enroll_identity(
    id: uuid.UUID,
    req: DatasetEnrollRequest,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
) -> DatasetIdentityResponse:
    dataset_service = DatasetService(session)
    identity = await dataset_service.enroll_identity(
        dataset_id=id,
        identity_code=req.identity_code,
        full_name=req.full_name,
        role_title=req.role_title,
        department=req.department,
        photo_url=req.photo_url,
        metadata_json=req.metadata,
        actor_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    await session.commit()

    return DatasetIdentityResponse(
        id=identity.id,
        identity_code=identity.identity_code,
        full_name=identity.full_name,
        role_title=identity.role_title,
        department=identity.department,
        photo_url=identity.photo_url,
    )


@router.get("/{id}/readiness", response_model=DatasetReadinessResponse, summary="Get Dataset Readiness Report")
async def get_dataset_readiness(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DatasetReadinessResponse:
    dataset_service = DatasetService(session)
    report = await dataset_service.get_readiness_report(id)
    return DatasetReadinessResponse(
        dataset_id=report.dataset_id,
        dataset_name=report.dataset_name,
        version=report.version,
        total_records=report.total_records,
        valid_records=report.valid_records,
        invalid_records=report.invalid_records,
        indexed_identities=report.indexed_identities,
        embedding_status=report.embedding_status,
        is_ready_for_matching=report.is_ready_for_matching,
    )
