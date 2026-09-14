"""Evidence service for uploading, linking, and retrieving artifacts."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.audit_log import AuditAction
from app.models.evidence import Evidence, EvidenceType
from app.repositories.evidence import EvidenceRepository
from app.schemas.evidence import EvidenceCreate
from app.services.audit import AuditService
from app.storage.backend import get_storage


class EvidenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EvidenceRepository(session)
        self.audit = AuditService(session)
        self.storage = get_storage()

    async def get_evidence(self, evidence_id: uuid.UUID, organization_id: uuid.UUID) -> Evidence:
        evidence = await self.repo.get_by_id_and_org(evidence_id, organization_id)
        if not evidence:
            raise NotFoundError(f"Evidence {evidence_id} not found")
        return evidence

    async def list_evidence(
        self,
        organization_id: uuid.UUID,
        analysis_id: Optional[uuid.UUID] = None,
        incident_id: Optional[uuid.UUID] = None,
        evidence_type: Optional[EvidenceType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Evidence], int]:
        return await self.repo.list_by_parent(
            organization_id=organization_id,
            analysis_id=analysis_id,
            incident_id=incident_id,
            evidence_type=evidence_type,
            limit=limit,
            offset=offset,
        )

    async def create_evidence(
        self,
        organization_id: uuid.UUID,
        evidence_in: EvidenceCreate,
        file_bytes: Optional[bytes] = None,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Evidence:
        if not evidence_in.analysis_id and not evidence_in.incident_id:
            raise ValidationError("Evidence must be associated with an analysis or incident")

        storage_path = evidence_in.storage_path
        sha256_hash = evidence_in.sha256
        file_size = evidence_in.file_size_bytes
        mime_type = evidence_in.mime_type

        # If raw file bytes provided, persist to storage
        if file_bytes is not None:
            storage_path, sha256_hash, file_size, mime_type = await self.storage.save(
                content=file_bytes,
                filename=evidence_in.original_filename,
                subfolder="evidence",
            )

        evidence = await self.repo.create(
            analysis_id=evidence_in.analysis_id,
            incident_id=evidence_in.incident_id,
            uploaded_by_id=actor_id,
            evidence_type=evidence_in.evidence_type,
            title=evidence_in.title,
            description=evidence_in.description,
            storage_path=storage_path,
            original_filename=evidence_in.original_filename,
            mime_type=mime_type,
            file_size_bytes=file_size,
            sha256=sha256_hash,
            content=evidence_in.content,
            url=evidence_in.url,
            metadata_=evidence_in.metadata_ or {},
        )

        await self.audit.log(
            organization_id=organization_id,
            action=AuditAction.create,
            target_type="evidence",
            target_id=str(evidence.id),
            user_id=actor_id,
            details={"type": evidence.evidence_type.value, "title": evidence.title},
        )

        return evidence

    async def get_evidence_bytes(self, evidence_id: uuid.UUID, organization_id: uuid.UUID) -> bytes:
        evidence = await self.get_evidence(evidence_id, organization_id)
        if evidence.storage_path:
            return await self.storage.read(evidence.storage_path)
        elif evidence.content:
            return evidence.content.encode("utf-8")
        raise NotFoundError("Evidence has no associated file or content")
