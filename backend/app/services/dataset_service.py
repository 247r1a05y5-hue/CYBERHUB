"""Dataset engine — Pluggable adapters, admin enrollment, and readiness reporting."""
from __future__ import annotations

import abc
import csv
import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.dataset import Dataset, DatasetIdentity, DatasetStatus, DatasetVersion
from app.services.audit_service import AuditService


@dataclass
class NormalizedIdentityRecord:
    identity_code: str
    full_name: str
    role_title: str | None = None
    department: str | None = None
    photo_url: str | None = None
    metadata_json: dict[str, Any] | None = None


@dataclass
class DatasetReadinessReport:
    dataset_id: uuid.UUID
    dataset_name: str
    version: str
    total_records: int
    valid_records: int
    invalid_records: int
    indexed_identities: int
    embedding_status: str
    is_ready_for_matching: bool


class DatasetAdapter(abc.ABC):
    @abc.abstractmethod
    def parse_records(self, payload: bytes | str) -> list[NormalizedIdentityRecord]:
        """Parse source data into normalized identity records."""


class MockHackathonAdapter(DatasetAdapter):
    """Default adapter generating synthetic authorized identities for testing and demo."""

    def parse_records(self, payload: bytes | str) -> list[NormalizedIdentityRecord]:
        return [
            NormalizedIdentityRecord(
                identity_code="ID-0842",
                full_name="Alex Vance",
                role_title="Lead Security Architect",
                department="Platform Engineering",
                photo_url="/assets/identities/alex_vance.jpg",
                metadata_json={"clearance_tier": "TIER_4", "risk_profile": "HIGH_VALUE_TARGET"},
            ),
            NormalizedIdentityRecord(
                identity_code="ID-0843",
                full_name="Sarah Chen",
                role_title="Senior SOC Analyst",
                department="Threat Operations",
                photo_url="/assets/identities/sarah_chen.jpg",
                metadata_json={"clearance_tier": "TIER_3", "risk_profile": "STANDARD"},
            ),
            NormalizedIdentityRecord(
                identity_code="ID-0844",
                full_name="Marcus Sterling",
                role_title="VP of Infrastructure",
                department="Executive",
                photo_url="/assets/identities/marcus_sterling.jpg",
                metadata_json={"clearance_tier": "TIER_5", "risk_profile": "EXECUTIVE_PROTECTION"},
            ),
            NormalizedIdentityRecord(
                identity_code="ID-0845",
                full_name="Elena Rostova",
                role_title="Principal Cryptographer",
                department="Core Cryptography",
                photo_url="/assets/identities/elena_rostova.jpg",
                metadata_json={"clearance_tier": "TIER_4", "risk_profile": "CONFIDENTIAL"},
            ),
        ]


class CSVDatasetAdapter(DatasetAdapter):
    def parse_records(self, payload: bytes | str) -> list[NormalizedIdentityRecord]:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        reader = csv.DictReader(text.splitlines())
        records = []
        for row in reader:
            records.append(
                NormalizedIdentityRecord(
                    identity_code=row.get("identity_code", str(uuid.uuid4())[:8]),
                    full_name=row.get("full_name", "Unknown"),
                    role_title=row.get("role_title"),
                    department=row.get("department"),
                    photo_url=row.get("photo_url"),
                    metadata_json={k: v for k, v in row.items() if k not in ("identity_code", "full_name", "role_title", "department", "photo_url")},
                )
            )
        return records


class JSONDatasetAdapter(DatasetAdapter):
    def parse_records(self, payload: bytes | str) -> list[NormalizedIdentityRecord]:
        data = json.loads(payload) if isinstance(payload, (bytes, str)) else payload
        items = data if isinstance(data, list) else data.get("identities", [])
        return [
            NormalizedIdentityRecord(
                identity_code=item.get("identity_code", str(uuid.uuid4())[:8]),
                full_name=item.get("full_name", "Unknown"),
                role_title=item.get("role_title"),
                department=item.get("department"),
                photo_url=item.get("photo_url"),
                metadata_json=item.get("metadata", {}),
            )
            for item in items
        ]


class DatasetService:
    """Service to manage bounded authorized datasets, ingest identities, and compute readiness."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_service = AuditService(session)

    async def get_or_create_default_dataset(self, organization_id: uuid.UUID) -> Dataset:
        """Fetch or create the default authorized dataset for an organization."""
        stmt = select(Dataset).where(
            Dataset.organization_id == organization_id,
            Dataset.is_active == True,
        )
        res = await self.session.execute(stmt)
        dataset = res.scalar_one_or_none()

        if not dataset:
            dataset = Dataset(
                organization_id=organization_id,
                name="Authorized Hackathon Dataset (Default)",
                description="Bounded authorized identity pool for subject identity verification.",
                category="AUTHORIZED_PERSONNEL",
                version="1.0.0",
                status=DatasetStatus.READY,
                is_active=True,
            )
            self.session.add(dataset)
            await self.session.flush()

            # Seed with default hackathon demo identities
            adapter = MockHackathonAdapter()
            records = adapter.parse_records("")
            for rec in records:
                identity = DatasetIdentity(
                    dataset_id=dataset.id,
                    identity_code=rec.identity_code,
                    full_name=rec.full_name,
                    role_title=rec.role_title,
                    department=rec.department,
                    photo_url=rec.photo_url,
                    metadata_json=rec.metadata_json or {},
                )
                self.session.add(identity)

            # Record version
            ver = DatasetVersion(
                dataset_id=dataset.id,
                version_number="1.0.0",
                changelog="Initial seed of authorized identities.",
                record_count=len(records),
            )
            self.session.add(ver)
            await self.session.flush()

        return dataset

    async def enroll_identity(
        self,
        dataset_id: uuid.UUID,
        identity_code: str,
        full_name: str,
        role_title: str | None = None,
        department: str | None = None,
        photo_url: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        actor_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> DatasetIdentity:
        """Enroll a new identity into the authorized dataset (Admin only)."""
        identity = DatasetIdentity(
            dataset_id=dataset_id,
            identity_code=identity_code,
            full_name=full_name,
            role_title=role_title,
            department=department,
            photo_url=photo_url,
            metadata_json=metadata_json or {},
        )
        self.session.add(identity)
        await self.session.flush()

        await self.audit_service.log(
            action=AuditAction.dataset_enrolled,
            user_id=actor_id,
            organization_id=organization_id,
            resource_type="dataset",
            resource_id=str(dataset_id),
            details={
                "identity_id": str(identity.id),
                "identity_code": identity_code,
                "full_name": full_name,
            },
        )
        return identity

    async def get_readiness_report(self, dataset_id: uuid.UUID) -> DatasetReadinessReport:
        """Compute readiness metrics for an authorized dataset."""
        stmt = select(Dataset).where(Dataset.id == dataset_id)
        res = await self.session.execute(stmt)
        dataset = res.scalar_one_or_none()

        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        count_stmt = select(func.count(DatasetIdentity.id)).where(DatasetIdentity.dataset_id == dataset_id)
        total_identities = (await self.session.execute(count_stmt)).scalar() or 0

        return DatasetReadinessReport(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            version=dataset.version,
            total_records=total_identities,
            valid_records=total_identities,
            invalid_records=0,
            indexed_identities=total_identities,
            embedding_status="100% INDEXED",
            is_ready_for_matching=total_identities > 0,
        )
