"""Dataset Matching Service — Biometric Face Query Pipeline.

Pipeline:
Query Image
    ↓
Image Validation (MIME, size, decompression bomb protection)
    ↓
Face Detection (0 -> NO_FACE, 1 -> PROCEED, >1 -> MULTIPLE_FACES)
    ↓
Face Quality Gate (Sharpness, lighting, resolution)
    ↓
Face Alignment (Canonical 112x112 crop)
    ↓
ArcFace 512-d Embedding
    ↓
Qdrant Vector Similarity Search (Tenant isolated)
    ↓
Candidate Retrieval & Scoring
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.biometrics import FaceValidationStatus
from app.models.participant import (
    ConsentStatus,
    DatasetMatch,
    MatchStatus,
    Participant,
    ParticipantImage,
    ParticipantPublicSource,
)
from app.services.aws_rekognition_service import rekognition_service
from app.services.face_detection_service import face_detection_service
from app.services.face_embedding_service import face_embedding_service
from app.services.image_validation_service import ImageValidationError, ImageValidationService
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


class MatchOutcomeStatus(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    INSUFFICIENT_QUALITY = "INSUFFICIENT_QUALITY"
    NO_FACE = "NO_FACE"
    MULTIPLE_FACES = "MULTIPLE_FACES"


@dataclass
class CandidateIdentity:
    """Structured, safe participant candidate record (Zero raw embeddings or stored face images)."""
    participant_id: str
    name: str
    custom_id: str | None
    similarity: float  # Visual cosine similarity in [0, 1]
    confidence: float
    confirmed_urls: list[str] = field(default_factory=list)
    match_status: str = "CONFIRMED_MATCH"


@dataclass
class DatasetMatchResponse:
    """Response returned by dataset match pipeline."""
    status: MatchOutcomeStatus
    message: str
    candidates: list[CandidateIdentity] = field(default_factory=list)
    top_match: CandidateIdentity | None = None
    face_count: int = 0
    quality_score: float = 0.0
    query_phash: str | None = None
    query_dhash: str | None = None
    backend_used: str = "LOCAL_ARCFACE"


class DatasetMatchingService:
    """Service to execute end-to-end face search across authorized datasets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def match_image(
        self,
        image_bytes: bytes,
        organization_id: uuid.UUID,
        top_k: int = 5,
        similarity_threshold: float = 0.60,
        preferred_backend: str = "LOCAL_ARCFACE",
    ) -> DatasetMatchResponse:
        """Execute complete query image validation, detection, embedding, and vector search."""

        # 1. Image Validation
        try:
            val_meta = ImageValidationService.validate_and_sanitize(image_bytes)
        except ImageValidationError as val_err:
            return DatasetMatchResponse(
                status=MatchOutcomeStatus.INSUFFICIENT_QUALITY,
                message=f"Image validation failed: {val_err}",
            )

        # 2. Face Detection & Quality Validation
        det = face_detection_service.detect_and_validate(image_bytes)

        if det.status == FaceValidationStatus.NO_FACE:
            return DatasetMatchResponse(
                status=MatchOutcomeStatus.NO_FACE,
                message="No face detected in the query image. Please provide a clear portrait photo.",
                face_count=0,
                query_phash=val_meta.phash,
                query_dhash=val_meta.dhash,
            )

        if det.status == FaceValidationStatus.MULTIPLE_FACES:
            return DatasetMatchResponse(
                status=MatchOutcomeStatus.MULTIPLE_FACES,
                message=f"Multiple faces ({det.face_count}) detected. Please upload an image with a single person.",
                face_count=det.face_count,
                query_phash=val_meta.phash,
                query_dhash=val_meta.dhash,
            )

        if det.status == FaceValidationStatus.POOR_QUALITY:
            return DatasetMatchResponse(
                status=MatchOutcomeStatus.INSUFFICIENT_QUALITY,
                message=det.error_message or "Face quality is insufficient for biometric comparison.",
                face_count=1,
                quality_score=det.quality_score,
                query_phash=val_meta.phash,
                query_dhash=val_meta.dhash,
            )

        # Check interchangeable AWS Rekognition backend if requested and configured
        if preferred_backend == "AWS_REKOGNITION" and rekognition_service.is_configured:
            try:
                aws_res = rekognition_service.search_faces_by_image(
                    image_bytes=image_bytes,
                    similarity_threshold=similarity_threshold * 100,
                    max_faces=top_k,
                )
                if aws_res.matched and aws_res.top_match:
                    # Look up participant in DB
                    participant = await self._find_participant_by_external_id(
                        organization_id, aws_res.top_match.external_image_id
                    )
                    if participant:
                        urls = await self._get_participant_urls(participant.id)
                        candidate = CandidateIdentity(
                            participant_id=str(participant.id),
                            name=participant.full_name,
                            custom_id=participant.custom_id,
                            similarity=round(aws_res.top_match.similarity / 100.0, 3),
                            confidence=round(aws_res.top_match.confidence / 100.0, 3),
                            confirmed_urls=urls,
                        )
                        return DatasetMatchResponse(
                            status=MatchOutcomeStatus.MATCH,
                            message="Participant matched via AWS Rekognition index.",
                            candidates=[candidate],
                            top_match=candidate,
                            face_count=1,
                            quality_score=det.quality_score,
                            query_phash=val_meta.phash,
                            query_dhash=val_meta.dhash,
                            backend_used="AWS_REKOGNITION",
                        )
            except Exception as aws_err:
                logger.warning(f"AWS Rekognition query failed ({aws_err}); falling back to Local ArcFace.")

        # 3. Local ArcFace 512-d Embedding Generation
        try:
            aligned_arr = det.primary_face.aligned_crop if det.primary_face else None
            if aligned_arr is not None:
                query_vector = face_embedding_service.embed_aligned_face(aligned_arr)
            else:
                query_vector = face_embedding_service.embed(image_bytes)
        except Exception as emb_err:
            logger.error(f"ArcFace embedding generation failed: {emb_err}")
            return DatasetMatchResponse(
                status=MatchOutcomeStatus.INSUFFICIENT_QUALITY,
                message=f"Biometric feature extraction failed: {emb_err}",
                face_count=1,
                quality_score=det.quality_score,
            )

        # 4. Qdrant Vector Similarity Search with Tenant Isolation
        similar_points = await qdrant_service.search_similar_faces(
            query_vector=query_vector,
            organization_id=organization_id,
            limit=top_k,
            score_threshold=similarity_threshold,
        )

        if not similar_points:
            return DatasetMatchResponse(
                status=MatchOutcomeStatus.NO_MATCH,
                message="No matching identities found in the authorized dataset above similarity threshold.",
                candidates=[],
                face_count=1,
                quality_score=det.quality_score,
                query_phash=val_meta.phash,
                query_dhash=val_meta.dhash,
                backend_used="LOCAL_ARCFACE",
            )

        # 5. Hydrate Candidates from Database
        candidates: list[CandidateIdentity] = []
        seen_p_ids: set[str] = set()

        for pt in similar_points:
            p_id_str = pt.participant_id
            if not p_id_str or p_id_str in seen_p_ids:
                continue
            seen_p_ids.add(p_id_str)

            try:
                p_uuid = uuid.UUID(p_id_str)
                stmt = select(Participant).where(
                    Participant.id == p_uuid,
                    Participant.organization_id == organization_id,
                    Participant.is_active == True,
                )
                res = await self.session.execute(stmt)
                participant = res.scalar_one_or_none()

                if participant:
                    urls = await self._get_participant_urls(participant.id)
                    candidates.append(
                        CandidateIdentity(
                            participant_id=str(participant.id),
                            name=participant.full_name,
                            custom_id=participant.custom_id,
                            similarity=round(pt.score, 3),
                            confidence=round(pt.score, 3),
                            confirmed_urls=urls,
                        )
                    )
            except Exception as e:
                logger.error(f"Candidate hydration error for {p_id_str}: {e}")

        top_match = candidates[0] if candidates else None
        status = MatchOutcomeStatus.MATCH if candidates else MatchOutcomeStatus.NO_MATCH
        message = (
            f"Found {len(candidates)} matching candidate(s) in dataset."
            if candidates
            else "No candidate identities confirmed."
        )

        return DatasetMatchResponse(
            status=status,
            message=message,
            candidates=candidates,
            top_match=top_match,
            face_count=1,
            quality_score=det.quality_score,
            query_phash=val_meta.phash,
            query_dhash=val_meta.dhash,
            backend_used="LOCAL_ARCFACE",
        )

    async def _get_participant_urls(self, participant_id: uuid.UUID) -> list[str]:
        """Fetch confirmed public URLs for a participant (Zero face images returned)."""
        stmt = select(ParticipantPublicSource.source_url).where(
            ParticipantPublicSource.participant_id == participant_id,
            ParticipantPublicSource.is_verified == True,
        )
        res = await self.session.execute(stmt)
        return [str(row[0]) for row in res.fetchall() if row[0]]

    async def _find_participant_by_external_id(
        self, organization_id: uuid.UUID, external_id: str
    ) -> Participant | None:
        """Lookup participant by AWS external image ID or custom ID."""
        stmt = select(Participant).where(
            Participant.organization_id == organization_id,
            Participant.custom_id == external_id,
            Participant.is_active == True,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
