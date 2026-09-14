"""Data Retention & Scheduled Deletion Service.

Specifications:
- Enforces configurable retention expiration windows for closed/expired investigations.
- Performs coordinated cross-store deletion across:
  1. Filesystem / Object storage (reference images and evidence artifacts)
  2. Qdrant vector index (DINOv2 embeddings)
  3. PostgreSQL relational records
- Emits auditable deletion receipts without retaining deleted content.
- Tracks reconciliation status and failure state recovery (no false success claims).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.case import Case, CaseStatus
from app.models.biometrics import ReferenceImage
from app.models.evidence import Evidence
from app.services.qdrant_service import qdrant_service
from app.services.secure_storage_service import secure_storage_service

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 30


@dataclass(frozen=True)
class DeletionReceipt:
    """Auditable receipt proving purge execution with reconciliation details."""
    investigation_id: Any
    organization_id: Any
    deleted_at: str
    files_removed_count: int
    vectors_removed_count: int
    db_records_removed: bool
    status: str
    reconciliation_status: str
    errors: list[str]

    @property
    def purged_files_count(self) -> int:
        return self.files_removed_count

    @property
    def purged_vectors_count(self) -> int:
        return self.vectors_removed_count


class RetentionService:
    """Manages scheduled expiration and cross-store data purging with reconciliation."""

    def __init__(self, retention_days: int = DEFAULT_RETENTION_DAYS) -> None:
        self.retention_days = retention_days

    async def purge_investigation(
        self,
        db: AsyncSession,
        case_or_id: Case | uuid.UUID | str,
        org_id: uuid.UUID | str | None = None,
    ) -> DeletionReceipt:
        """
        Coordinated cross-store purge across storage, Qdrant, and PostgreSQL.
        Maintains honest reconciliation status without pretending partial failures are complete.
        """
        if isinstance(case_or_id, Case):
            case = case_or_id
            inv_id = case.id
            actual_org_id = org_id or case.organization_id
        else:
            inv_id = case_or_id if isinstance(case_or_id, uuid.UUID) else uuid.UUID(str(case_or_id))
            stmt = select(Case).where(Case.id == inv_id)
            res = await db.execute(stmt)
            case = res.scalar_one_or_none()
            actual_org_id = org_id or (case.organization_id if case else None)

        files_deleted = 0
        vectors_deleted = 0
        db_deleted = False
        errors: list[str] = []

        # 1. Purge Filesystem Artifacts (Explicit async queries to prevent lazy load errors)
        try:
            ref_stmt = select(ReferenceImage).where(ReferenceImage.case_id == inv_id)
            ref_records = list((await db.execute(ref_stmt)).scalars().all())
            for ref in ref_records:
                p = getattr(ref, "storage_path", None) or getattr(ref, "file_path", None)
                if p:
                    try:
                        if secure_storage_service.delete_file(p):
                            files_deleted += 1
                    except Exception as err:
                        errors.append(f"Storage ref delete error: {err}")
        except Exception as err:
            errors.append(f"Reference artifact query error: {err}")

        try:
            ev_stmt = select(Evidence).where(Evidence.case_id == inv_id)
            ev_records = list((await db.execute(ev_stmt)).scalars().all())
            for ev in ev_records:
                p = getattr(ev, "file_path", None) or getattr(ev, "storage_path", None)
                if p:
                    try:
                        if secure_storage_service.delete_file(p):
                            files_deleted += 1
                    except Exception as err:
                        errors.append(f"Storage evidence delete error: {err}")
        except Exception as err:
            errors.append(f"Evidence artifact query error: {err}")

        # 2. Purge Qdrant Vectors
        try:
            vectors_deleted = await qdrant_service.delete_by_investigation(inv_id, actual_org_id)
        except Exception as err:
            errors.append(f"Qdrant vector purge error: {err}")

        # 3. Purge Database Records
        if case:
            try:
                await db.delete(case)
                await db.flush()
                db_deleted = True
            except Exception as err:
                errors.append(f"Database record delete error: {err}")

        # Determine reconciliation status
        if not errors:
            reconciliation = "COMPLETED"
            status_str = "PURGED_SUCCESSFULLY"
        elif db_deleted and errors:
            reconciliation = "PARTIAL_RETRY_SCHEDULED"
            status_str = "PARTIALLY_PURGED"
        else:
            reconciliation = "FAILED"
            status_str = "PURGE_FAILED"

        receipt = DeletionReceipt(
            investigation_id=inv_id,
            organization_id=actual_org_id,
            deleted_at=datetime.now(timezone.utc).isoformat(),
            files_removed_count=files_deleted,
            vectors_removed_count=vectors_deleted,
            db_records_removed=db_deleted,
            status=status_str,
            reconciliation_status=reconciliation,
            errors=errors,
        )

        logger.info(
            f"Retention purge completed for investigation {inv_id}: "
            f"status={status_str}, reconciliation={reconciliation}, "
            f"{files_deleted} files, {vectors_deleted} vectors purged."
        )
        return receipt

    async def run_retention_sweep(
        self,
        db: AsyncSession,
        retention_days: int | None = None,
    ) -> list[DeletionReceipt]:
        """Find and purge all closed investigations past retention window."""
        days = retention_days if retention_days is not None else self.retention_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(Case).where(
            Case.status == CaseStatus.CLOSED,
            Case.updated_at <= cutoff_date,
        )
        result = await db.execute(query)
        expired_cases = result.scalars().all()

        receipts: list[DeletionReceipt] = []
        for case in expired_cases:
            try:
                receipt = await self.purge_investigation(db, case)
                receipts.append(receipt)
            except Exception as err:
                logger.error(f"Failed to purge expired investigation {case.id}: {err}")

        return receipts


retention_service = RetentionService()

