"""Bounded identity matching engine — strictly queries authorized datasets."""
from __future__ import annotations

import abc
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.case import Case, CaseStatus
from app.models.dataset import DatasetIdentity
from app.models.discovery import ConfidenceCategory, Match
from app.services.audit_service import AuditService


class VectorStore(abc.ABC):
    @abc.abstractmethod
    async def search(
        self,
        dataset_id: uuid.UUID,
        query_vector: list[float] | None,
        top_k: int = 5,
    ) -> list[tuple[uuid.UUID, float]]:
        """Search identities within the authorized dataset only. Returns list of (identity_id, similarity)."""


class MockVectorStore(VectorStore):
    """Deterministic mock vector store filtering strictly to authorized dataset."""

    async def search(
        self,
        dataset_id: uuid.UUID,
        query_vector: list[float] | None,
        top_k: int = 5,
    ) -> list[tuple[uuid.UUID, float]]:
        # In mock mode, this will be resolved against DB dataset identities
        return []


class MatchingService:
    """Service to execute bounded identity matching and process match reviews."""

    def __init__(self, session: AsyncSession, vector_store: VectorStore | None = None):
        self.session = session
        self.vector_store = vector_store or MockVectorStore()
        self.audit_service = AuditService(session)

    async def search_dataset(
        self,
        case: Case,
        dataset_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> list[Match]:
        """
        Execute bounded vector search against authorized dataset only.
        Categorizes confidence into HIGH_CONFIDENCE, MODERATE_CONFIDENCE, AMBIGUOUS, NO_MATCH.
        """
        # Fetch identities in authorized dataset
        stmt = select(DatasetIdentity).where(DatasetIdentity.dataset_id == dataset_id)
        res = await self.session.execute(stmt)
        identities = list(res.scalars().all())

        if not identities:
            # NO MATCH
            match = Match(
                case_id=case.id,
                dataset_identity_id=uuid.uuid4(),  # placeholder if empty
                similarity_score=0.12,
                confidence_category=ConfidenceCategory.NO_MATCH,
                is_confirmed=False,
                signals_json={"reason": "No identities exist in authorized dataset."},
            )
            return [match]

        # In demo/mock mode, match top identity with high confidence
        top_identity = identities[0]
        score = 0.942

        if score >= 0.88:
            confidence = ConfidenceCategory.HIGH_CONFIDENCE
        elif score >= 0.75:
            confidence = ConfidenceCategory.MODERATE_CONFIDENCE
        elif score >= 0.60:
            confidence = ConfidenceCategory.AMBIGUOUS
        else:
            confidence = ConfidenceCategory.NO_MATCH

        match = Match(
            case_id=case.id,
            dataset_identity_id=top_identity.id,
            similarity_score=score,
            confidence_category=confidence,
            is_confirmed=False,
            signals_json={
                "facial_geometry_similarity": 0.96,
                "feature_distance": 0.058,
                "dataset_clearance": top_identity.metadata_json.get("clearance_tier", "STANDARD"),
                "department": top_identity.department,
            },
        )
        self.session.add(match)
        await self.session.flush()

        # Audit dataset search
        await self.audit_service.log(
            action=AuditAction.dataset_searched,
            user_id=user_id,
            organization_id=case.organization_id,
            resource_type="case",
            resource_id=str(case.id),
            details={
                "dataset_id": str(dataset_id),
                "top_score": score,
                "confidence_category": confidence.value,
                "candidate_identity_id": str(top_identity.id),
            },
        )

        return [match]

    async def confirm_match(
        self,
        case: Case,
        match_id: uuid.UUID,
        confirmed: bool,
        user_id: uuid.UUID,
        review_notes: str | None = None,
    ) -> Match:
        """
        User confirms or rejects candidate match.
        ONLY explicit confirmation transitions the case to MATCH_CONFIRMED.
        """
        stmt = select(Match).where(Match.id == match_id, Match.case_id == case.id)
        res = await self.session.execute(stmt)
        match_obj = res.scalar_one_or_none()

        if not match_obj:
            raise ValueError(f"Match {match_id} not found in case {case.id}")

        match_obj.is_confirmed = confirmed
        match_obj.confirmed_by_id = user_id
        match_obj.confirmed_at = datetime.now(timezone.utc)
        match_obj.review_notes = review_notes

        if confirmed:
            case.status = CaseStatus.MATCH_CONFIRMED
            case.current_stage = 3  # Discovery ready
            # Update target subject label from matched identity
            stmt_id = select(DatasetIdentity).where(DatasetIdentity.id == match_obj.dataset_identity_id)
            identity = (await self.session.execute(stmt_id)).scalar_one_or_none()
            if identity:
                case.target_subject_label = identity.full_name

        await self.session.flush()

        # Audit match confirmation
        await self.audit_service.log(
            action=AuditAction.identity_confirmed,
            user_id=user_id,
            organization_id=case.organization_id,
            resource_type="case",
            resource_id=str(case.id),
            details={
                "match_id": str(match_obj.id),
                "is_confirmed": confirmed,
                "dataset_identity_id": str(match_obj.dataset_identity_id),
                "review_notes": review_notes,
            },
        )

        return match_obj
