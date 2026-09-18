"""Participant service — enrollment, image validation, indexing, matching, deletion.

Privacy invariant (enforced here and at the API layer):
  ParticipantImage.storage_key and any raw file path MUST NEVER
  appear in return values that surface to the API response layer.
"""
from __future__ import annotations

import hashlib
import io
import logging
import mimetypes
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditAction
from app.models.participant import (
    ConsentStatus,
    DatasetMatch,
    DatasetVerification,
    ImageIndexStatus,
    MatchStatus,
    Participant,
    ParticipantConsent,
    ParticipantImage,
    ParticipantPublicSource,
    VerificationStatus,
)
from app.services.audit_service import AuditService
from app.services.aws_rekognition_service import rekognition_service

logger = logging.getLogger(__name__)

# Magic-byte signatures for supported image types
_MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",  # checked further below
    b"GIF8": "image/gif",
}

_ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB (AWS hard limit is 5 MB)
_MIN_DIMENSION = 32
_MAX_PIXELS = 100_000_000  # decompression bomb protection


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass
class ParticipantDetail:
    """Safe participant info for API responses — no storage keys."""
    id: uuid.UUID
    organization_id: uuid.UUID
    participant_code: str
    display_name: str
    consent_status: str
    consent_timestamp: datetime | None
    is_active: bool
    image_count: int
    indexed_image_count: int
    source_count: int


@dataclass
class ImageDetail:
    """Safe image info — never includes storage_key."""
    id: uuid.UUID
    participant_id: uuid.UUID
    mime_type: str
    file_size_bytes: int
    width: int | None
    height: int | None
    sha256: str
    phash: str | None
    dhash: str | None
    aws_face_id: str | None
    aws_external_image_id: str | None
    index_status: str
    index_error: str | None
    aws_indexed_at: datetime | None
    face_confidence: float | None
    image_sequence: int


@dataclass
class MatchCandidate:
    """Result of a dataset match — never includes image URLs or storage keys."""
    match_id: uuid.UUID
    participant_id: uuid.UUID
    participant_code: str
    display_name: str
    aws_similarity: float
    aws_face_id: str
    aws_external_image_id: str
    match_status: str
    matched_at: datetime
    public_sources: list[dict[str, Any]] = field(default_factory=list)
    # Local secondary metrics — NEVER blended with aws_similarity
    local_similarity: float | None = None
    local_match_method: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class DatasetStats:
    participant_count: int
    image_count: int
    indexed_face_count: int
    source_count: int
    consent_pending_count: int
    last_match_at: datetime | None


# ---------------------------------------------------------------------------
# Image validation helpers
# ---------------------------------------------------------------------------


def _detect_mime(data: bytes) -> str:
    for magic, mime in _MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            if mime == "image/webp" and len(data) >= 12:
                if data[8:12] == b"WEBP":
                    return "image/webp"
                return "application/octet-stream"
            return mime
    return "application/octet-stream"


def _compute_hashes(data: bytes, img: Any) -> tuple[str, str | None, str | None]:
    """Return (sha256, phash, dhash)."""
    sha256 = hashlib.sha256(data).hexdigest()
    phash: str | None = None
    dhash: str | None = None
    try:
        import imagehash

        phash = str(imagehash.phash(img))
        dhash = str(imagehash.dhash(img))
    except ImportError:
        logger.warning("imagehash not installed — pHash/dHash skipped")
    except Exception as e:
        logger.warning(f"Hash computation failed: {e}")
    return sha256, phash, dhash


def validate_and_decode_image(data: bytes) -> tuple[Any, str, int, int]:
    """Validate image bytes and return (PIL.Image, mime_type, width, height).

    Raises ValueError with a descriptive message on failure.
    """
    from PIL import Image, UnidentifiedImageError

    if len(data) > _MAX_IMAGE_BYTES:
        raise ValueError(f"Image too large: {len(data)} bytes (max {_MAX_IMAGE_BYTES})")

    mime = _detect_mime(data)
    if mime not in _ALLOWED_MIMES:
        raise ValueError(f"Unsupported image type detected by magic bytes: {mime}")

    try:
        buf = io.BytesIO(data)
        buf.seek(0)
        img = Image.open(buf)
        # Decompression bomb check
        if img.width * img.height > _MAX_PIXELS:
            raise ValueError("Image dimensions exceed maximum allowed pixel count (decompression bomb protection).")
        img.load()  # force decode
        if img.width < _MIN_DIMENSION or img.height < _MIN_DIMENSION:
            raise ValueError(f"Image too small: {img.width}x{img.height} (min {_MIN_DIMENSION}px each side)")
        img = img.convert("RGB")
        return img, mime, img.width, img.height
    except UnidentifiedImageError:
        raise ValueError("File cannot be decoded as an image.")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Image validation failed: {e}") from e


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ParticipantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditService(session)

    # ------------------------------------------------------------------
    # Participant CRUD
    # ------------------------------------------------------------------

    async def create_participant(
        self,
        organization_id: uuid.UUID,
        display_name: str,
        participant_code: str | None = None,
        notes: str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> Participant:
        """Create a participant with PENDING consent."""
        if not participant_code:
            # Generate a unique code
            count_stmt = select(func.count(Participant.id)).where(
                Participant.organization_id == organization_id
            )
            count = (await self.session.execute(count_stmt)).scalar() or 0
            participant_code = f"P{count + 1:04d}"

        participant = Participant(
            organization_id=organization_id,
            participant_code=participant_code,
            display_name=display_name,
            consent_status=ConsentStatus.PENDING,
            is_active=True,
            notes=notes,
        )
        self.session.add(participant)
        await self.session.flush()

        await self.audit.log(
            action=AuditAction.admin_action,
            user_id=actor_id,
            organization_id=organization_id,
            resource_type="participant",
            resource_id=str(participant.id),
            details={"event": "DATASET_PARTICIPANT_CREATED", "code": participant_code, "display_name": display_name},
        )
        return participant

    async def grant_consent(
        self,
        participant_id: uuid.UUID,
        organization_id: uuid.UUID,
        method: str = "ADMIN_ENROLLMENT",
        ip_address: str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> Participant:
        """Record consent and update participant.consent_status = CONSENTED."""
        stmt = select(Participant).where(
            Participant.id == participant_id,
            Participant.organization_id == organization_id,
        )
        participant = (await self.session.execute(stmt)).scalar_one_or_none()
        if not participant:
            raise ValueError("Participant not found")

        now = datetime.now(timezone.utc)
        participant.consent_status = ConsentStatus.CONSENTED
        participant.consent_timestamp = now

        consent = ParticipantConsent(
            participant_id=participant_id,
            organization_id=organization_id,
            consent_status=ConsentStatus.CONSENTED,
            consent_timestamp=now,
            consent_method=method,
            ip_address=ip_address,
        )
        self.session.add(consent)
        await self.session.flush()
        return participant

    async def get_participant(
        self, participant_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Participant | None:
        stmt = select(Participant).where(
            Participant.id == participant_id,
            Participant.organization_id == organization_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_participants(self, organization_id: uuid.UUID) -> list[Participant]:
        stmt = select(Participant).where(
            Participant.organization_id == organization_id,
            Participant.is_active == True,
        ).order_by(Participant.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------
    # Image upload & validation
    # ------------------------------------------------------------------

    async def add_participant_image(
        self,
        participant_id: uuid.UUID,
        organization_id: uuid.UUID,
        image_data: bytes,
        original_filename: str = "upload.jpg",
        actor_id: uuid.UUID | None = None,
    ) -> ImageDetail:
        """Validate, store, and register one participant image.

        Returns ImageDetail — never exposes storage_key.
        """
        # 1. Load participant and check consent
        participant = await self.get_participant(participant_id, organization_id)
        if not participant:
            raise ValueError("Participant not found")

        # 2. Validate image
        img, mime, width, height = validate_and_decode_image(image_data)

        # 3. Compute hashes
        sha256, phash, dhash = _compute_hashes(image_data, img)

        # 4. Idempotency — don't store duplicate SHA-256
        existing_stmt = select(ParticipantImage).where(
            ParticipantImage.organization_id == organization_id,
            ParticipantImage.sha256 == sha256,
        )
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            logger.info(f"Duplicate image sha256={sha256} for org={organization_id} — returning existing")
            return self._to_image_detail(existing)

        # 5. Store image (server-side only)
        seq_stmt = select(func.count(ParticipantImage.id)).where(
            ParticipantImage.participant_id == participant_id
        )
        seq = (await self.session.execute(seq_stmt)).scalar() or 0
        storage_key = f"participants/{participant_id}/img_{seq + 1:03d}_{sha256[:8]}.jpg"
        full_path = os.path.join(settings.storage_root, storage_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Re-encode as JPEG for consistent storage
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        jpeg_bytes = buf.getvalue()
        with open(full_path, "wb") as f:
            f.write(jpeg_bytes)

        # 6. Create DB record
        pimg = ParticipantImage(
            participant_id=participant_id,
            organization_id=organization_id,
            sha256=sha256,
            phash=phash,
            dhash=dhash,
            storage_key=storage_key,  # NEVER returned in API responses
            mime_type="image/jpeg",
            file_size_bytes=len(jpeg_bytes),
            width=width,
            height=height,
            index_status=ImageIndexStatus.PENDING,
            image_sequence=seq + 1,
        )
        self.session.add(pimg)
        await self.session.flush()

        await self.audit.log(
            action=AuditAction.admin_action,
            user_id=actor_id,
            organization_id=organization_id,
            resource_type="participant_image",
            resource_id=str(pimg.id),
            details={"event": "DATASET_IMAGE_UPLOADED", "participant_id": str(participant_id), "sha256": sha256},
        )
        return self._to_image_detail(pimg)

    # ------------------------------------------------------------------
    # AWS Indexing
    # ------------------------------------------------------------------

    async def index_participant_images(
        self,
        participant_id: uuid.UUID,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> list[ImageDetail]:
        """Index all PENDING images for a CONSENTED participant.

        Raises ValueError if participant has no valid consent.
        """
        participant = await self.get_participant(participant_id, organization_id)
        if not participant:
            raise ValueError("Participant not found")
        if participant.consent_status != ConsentStatus.CONSENTED:
            raise ValueError(
                f"Cannot index images — participant consent_status is {participant.consent_status}. "
                "Consent must be CONSENTED before indexing."
            )

        if not rekognition_service.is_configured:
            raise ValueError("AWS_NOT_CONFIGURED: AWS_REGION and AWS_REKOGNITION_COLLECTION_ID are required.")

        stmt = select(ParticipantImage).where(
            ParticipantImage.participant_id == participant_id,
            ParticipantImage.index_status.in_([ImageIndexStatus.PENDING, ImageIndexStatus.FAILED]),
        )
        images = list((await self.session.execute(stmt)).scalars().all())

        results: list[ImageDetail] = []
        for pimg in images:
            external_id = f"CYBERHUB:{participant.participant_code}:IMG{pimg.image_sequence:03d}"
            try:
                # Read from storage
                full_path = os.path.join(settings.storage_root, pimg.storage_key)
                with open(full_path, "rb") as f:
                    image_bytes = f.read()

                result = rekognition_service.index_face(
                    image_bytes=image_bytes,
                    external_image_id=external_id,
                )
                pimg.aws_face_id = result.face_id
                pimg.aws_external_image_id = result.external_image_id
                pimg.aws_collection_id = settings.AWS_REKOGNITION_COLLECTION_ID
                pimg.aws_indexed_at = datetime.now(timezone.utc)
                pimg.face_confidence = result.face_confidence
                pimg.index_status = ImageIndexStatus.INDEXED
                pimg.index_error = None

                await self.audit.log(
                    action=AuditAction.admin_action,
                    user_id=actor_id,
                    organization_id=organization_id,
                    resource_type="participant_image",
                    resource_id=str(pimg.id),
                    details={
                        "event": "DATASET_FACE_INDEXED",
                        "participant_id": str(participant_id),
                        "aws_face_id": result.face_id,
                        "external_image_id": external_id,
                    },
                )
                logger.info(f"Indexed face {result.face_id} for participant {participant_id}")

            except ValueError as ve:
                pimg.index_status = ImageIndexStatus.FAILED
                pimg.index_error = str(ve)
                logger.warning(f"Image validation failed during indexing: {ve}")
            except Exception as e:
                pimg.index_status = ImageIndexStatus.FAILED
                pimg.index_error = str(e)
                logger.error(f"AWS indexing failed for image {pimg.id}: {e}")

            await self.session.flush()
            results.append(self._to_image_detail(pimg))

        return results

    # ------------------------------------------------------------------
    # Public sources
    # ------------------------------------------------------------------

    async def add_public_source(
        self,
        participant_id: uuid.UUID,
        organization_id: uuid.UUID,
        platform: str,
        url: str,
        participant_confirmed: bool = True,
        actor_id: uuid.UUID | None = None,
    ) -> ParticipantPublicSource:
        """Add a participant-confirmed public URL."""
        participant = await self.get_participant(participant_id, organization_id)
        if not participant:
            raise ValueError("Participant not found")

        # Idempotency
        existing_stmt = select(ParticipantPublicSource).where(
            ParticipantPublicSource.participant_id == participant_id,
            ParticipantPublicSource.url == url,
        )
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            return existing

        source = ParticipantPublicSource(
            participant_id=participant_id,
            organization_id=organization_id,
            platform=platform.lower().strip(),
            url=url.strip(),
            participant_confirmed=participant_confirmed,
        )
        self.session.add(source)
        await self.session.flush()
        return source

    # ------------------------------------------------------------------
    # Camera match
    # ------------------------------------------------------------------

    async def match_face(
        self,
        organization_id: uuid.UUID,
        image_data: bytes,
        case_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        max_faces: int = 5,
        face_match_threshold: float = 80.0,
    ) -> MatchCandidate:
        """Run a real AWS SearchFacesByImage against the organization's indexed faces.

        Returns MatchCandidate — NEVER includes stored participant image.
        If multiple faces are in the query image, returns MULTIPLE_FACES_DETECTED.
        An AWS failure is NEVER the same thing as no match.
        """
        if not rekognition_service.is_configured:
            # Execute Local ArcFace + Qdrant face match pipeline
            from app.services.dataset_matching_service import DatasetMatchingService, MatchOutcomeStatus

            matching_svc = DatasetMatchingService(self.session)
            local_res = await matching_svc.match_image(
                image_bytes=image_data,
                organization_id=organization_id,
                top_k=max_faces,
                similarity_threshold=face_match_threshold / 100.0 if face_match_threshold > 1.0 else face_match_threshold,
                preferred_backend="LOCAL_ARCFACE",
            )

            # Persist DatasetMatch record
            match_status_enum = MatchStatus.CONFIRMED_MATCH if local_res.status == MatchOutcomeStatus.MATCH else MatchStatus.PENDING_REVIEW
            top_cand = local_res.top_match
            matched_p_id = uuid.UUID(top_cand.participant_id) if top_cand and top_cand.participant_id else None

            match = DatasetMatch(
                organization_id=organization_id,
                case_id=case_id,
                participant_id=matched_p_id,
                requested_by_id=actor_id,
                query_image_sha256=hashlib.sha256(image_data).hexdigest(),
                query_image_phash=local_res.query_phash,
                local_similarity=top_cand.similarity if top_cand else 0.0,
                local_match_method="ArcFace-r100",
                match_status=match_status_enum,
                error_code=local_res.status.value if local_res.status != MatchOutcomeStatus.MATCH else None,
                error_message=local_res.message,
                matched_at=datetime.now(timezone.utc),
            )
            self.session.add(match)
            await self.session.flush()

            sources = []
            if top_cand and matched_p_id:
                sources = await self.get_public_sources(matched_p_id, organization_id)
                source_dicts = [
                    {"id": str(s.id), "platform": s.platform, "url": s.url, "participant_confirmed": s.participant_confirmed}
                    for s in sources
                ]
            else:
                source_dicts = []

            return MatchCandidate(
                match_id=match.id,
                participant_id=matched_p_id or uuid.UUID(int=0),
                participant_code=top_cand.custom_id or "" if top_cand else "",
                display_name=top_cand.name if top_cand else "",
                aws_similarity=0.0,
                aws_face_id="",
                aws_external_image_id="",
                match_status=match_status_enum.value,
                matched_at=match.matched_at,
                public_sources=source_dicts,
                local_similarity=top_cand.similarity if top_cand else None,
                local_match_method="ArcFace-r100" if top_cand else None,
                error_code=local_res.status.value if local_res.status != MatchOutcomeStatus.MATCH else None,
                error_message=local_res.message,
            )

        sha256 = hashlib.sha256(image_data).hexdigest()
        phash: str | None = None
        try:
            img, _, _, _ = validate_and_decode_image(image_data)
            import imagehash
            phash = str(imagehash.phash(img))
        except Exception:
            pass

        await self.audit.log(
            action=AuditAction.admin_action,
            user_id=actor_id,
            organization_id=organization_id,
            resource_type="dataset_match",
            resource_id=None,
            details={"event": "DATASET_MATCH_REQUESTED", "sha256": sha256},
        )

        search_result = rekognition_service.search_faces_by_image(
            image_bytes=image_data,
            max_faces=max_faces,
            face_match_threshold=face_match_threshold,
        )

        if search_result.error_code and search_result.error_code not in ("NO_DATASET_MATCH",):
            # Infrastructure error — NOT the same as no match
            match = DatasetMatch(
                organization_id=organization_id,
                case_id=case_id,
                requested_by_id=actor_id,
                query_image_sha256=sha256,
                query_image_phash=phash,
                match_status=MatchStatus.PENDING_REVIEW,
                error_code=search_result.error_code,
                error_message=search_result.error_message,
                matched_at=datetime.now(timezone.utc),
            )
            self.session.add(match)
            await self.session.flush()

            await self.audit.log(
                action=AuditAction.admin_action,
                user_id=actor_id,
                organization_id=organization_id,
                resource_type="dataset_match",
                resource_id=str(match.id),
                details={"event": "DATASET_MATCH_FAILED", "error_code": search_result.error_code},
            )
            return MatchCandidate(
                match_id=match.id,
                participant_id=uuid.UUID(int=0),
                participant_code="",
                display_name="",
                aws_similarity=0.0,
                aws_face_id="",
                aws_external_image_id="",
                match_status=MatchStatus.PENDING_REVIEW.value,
                matched_at=match.matched_at,
                error_code=search_result.error_code,
                error_message=search_result.error_message,
            )

        if not search_result.matches:
            match = DatasetMatch(
                organization_id=organization_id,
                case_id=case_id,
                requested_by_id=actor_id,
                query_image_sha256=sha256,
                query_image_phash=phash,
                match_status=MatchStatus.PENDING_REVIEW,
                error_code="NO_DATASET_MATCH",
                error_message="No matching face found in the dataset.",
                matched_at=datetime.now(timezone.utc),
            )
            self.session.add(match)
            await self.session.flush()
            return MatchCandidate(
                match_id=match.id,
                participant_id=uuid.UUID(int=0),
                participant_code="",
                display_name="",
                aws_similarity=0.0,
                aws_face_id="",
                aws_external_image_id="",
                match_status=MatchStatus.PENDING_REVIEW.value,
                matched_at=match.matched_at,
                error_code="NO_DATASET_MATCH",
                error_message="No matching face found in the dataset.",
            )

        # Best match (AWS orders by similarity descending)
        best = search_result.matches[0]

        # Resolve AWS FaceId → ParticipantImage → Participant
        img_stmt = select(ParticipantImage).where(
            ParticipantImage.aws_face_id == best.face_id,
            ParticipantImage.organization_id == organization_id,
        )
        pimg = (await self.session.execute(img_stmt)).scalar_one_or_none()

        participant = None
        if pimg:
            participant = await self.get_participant(pimg.participant_id, organization_id)

        # Persist match record
        match = DatasetMatch(
            organization_id=organization_id,
            case_id=case_id,
            participant_id=participant.id if participant else None,
            requested_by_id=actor_id,
            query_image_sha256=sha256,
            query_image_phash=phash,
            aws_face_id_matched=best.face_id,
            aws_external_image_id=best.external_image_id,
            aws_similarity=best.similarity,
            aws_collection_id=settings.AWS_REKOGNITION_COLLECTION_ID,
            match_status=MatchStatus.PENDING_REVIEW,
            matched_at=datetime.now(timezone.utc),
        )
        self.session.add(match)
        await self.session.flush()

        # Fetch confirmed public sources
        public_sources: list[dict] = []
        if participant:
            src_stmt = select(ParticipantPublicSource).where(
                ParticipantPublicSource.participant_id == participant.id,
                ParticipantPublicSource.participant_confirmed == True,
            )
            sources = list((await self.session.execute(src_stmt)).scalars().all())
            public_sources = [
                {"platform": s.platform, "url": s.url}
                for s in sources
            ]

        await self.audit.log(
            action=AuditAction.admin_action,
            user_id=actor_id,
            organization_id=organization_id,
            resource_type="dataset_match",
            resource_id=str(match.id),
            details={
                "event": "DATASET_MATCH_COMPLETED",
                "aws_similarity": best.similarity,
                "participant_id": str(participant.id) if participant else None,
            },
        )

        return MatchCandidate(
            match_id=match.id,
            participant_id=participant.id if participant else uuid.UUID(int=0),
            participant_code=participant.participant_code if participant else best.external_image_id,
            display_name=participant.display_name if participant else "Unknown",
            aws_similarity=best.similarity,
            aws_face_id=best.face_id,
            aws_external_image_id=best.external_image_id,
            match_status=MatchStatus.PENDING_REVIEW.value,
            matched_at=match.matched_at,
            public_sources=public_sources,
        )

    # ------------------------------------------------------------------
    # Human verification
    # ------------------------------------------------------------------

    async def verify_match(
        self,
        match_id: uuid.UUID,
        organization_id: uuid.UUID,
        status: VerificationStatus,
        verification_note: str | None,
        actor_id: uuid.UUID,
    ) -> DatasetVerification:
        stmt = select(DatasetMatch).where(
            DatasetMatch.id == match_id,
            DatasetMatch.organization_id == organization_id,
        )
        match = (await self.session.execute(stmt)).scalar_one_or_none()
        if not match:
            raise ValueError("Match not found")

        now = datetime.now(timezone.utc)
        verification = DatasetVerification(
            match_id=match_id,
            organization_id=organization_id,
            status=status,
            verified_by=actor_id,
            verified_at=now,
            verification_note=verification_note,
        )
        self.session.add(verification)

        # Update match status to reflect verification
        if status == VerificationStatus.VERIFIED:
            match.match_status = MatchStatus.VERIFIED
        elif status == VerificationStatus.REJECTED:
            match.match_status = MatchStatus.REJECTED
        elif status == VerificationStatus.UNCERTAIN:
            match.match_status = MatchStatus.UNCERTAIN

        await self.session.flush()

        event = (
            "DATASET_MATCH_VERIFIED" if status == VerificationStatus.VERIFIED
            else "DATASET_MATCH_REJECTED"
        )
        await self.audit.log(
            action=AuditAction.result_verified,
            user_id=actor_id,
            organization_id=organization_id,
            resource_type="dataset_match",
            resource_id=str(match_id),
            details={"event": event, "status": status.value, "note": verification_note},
        )
        return verification

    # ------------------------------------------------------------------
    # Retry-safe deletion
    # ------------------------------------------------------------------

    async def delete_participant(
        self,
        participant_id: uuid.UUID,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Delete participant, their images, AWS FaceIds, and public sources.

        Partial failures are logged but don't abort the cleanup — orphaned data
        is always cleaned up on retry.
        """
        participant = await self.get_participant(participant_id, organization_id)
        if not participant:
            raise ValueError("Participant not found")

        report: dict[str, Any] = {
            "participant_id": str(participant_id),
            "aws_deleted_faces": [],
            "aws_errors": [],
            "storage_errors": [],
        }

        # 1. Delete AWS FaceIds
        img_stmt = select(ParticipantImage).where(
            ParticipantImage.participant_id == participant_id,
            ParticipantImage.aws_face_id.isnot(None),
        )
        indexed_images = list((await self.session.execute(img_stmt)).scalars().all())
        face_ids = [img.aws_face_id for img in indexed_images if img.aws_face_id]

        if face_ids and rekognition_service.is_configured:
            try:
                deleted = rekognition_service.delete_faces(face_ids)
                report["aws_deleted_faces"] = deleted
            except Exception as e:
                report["aws_errors"].append(str(e))
                logger.error(f"AWS face deletion partially failed for participant {participant_id}: {e}")

        # 2. Delete stored image files
        all_imgs_stmt = select(ParticipantImage).where(
            ParticipantImage.participant_id == participant_id
        )
        all_imgs = list((await self.session.execute(all_imgs_stmt)).scalars().all())
        for img in all_imgs:
            full_path = os.path.join(settings.storage_root, img.storage_key)
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as e:
                report["storage_errors"].append(str(e))
                logger.error(f"Failed to delete file {img.storage_key}: {e}")

        # 3. Soft-delete participant (cascade will handle DB records)
        participant.is_active = False
        await self.session.flush()
        await self.session.delete(participant)
        await self.session.flush()

        await self.audit.log(
            action=AuditAction.delete,
            user_id=actor_id,
            organization_id=organization_id,
            resource_type="participant",
            resource_id=str(participant_id),
            details={"event": "DATASET_PARTICIPANT_DELETED", **report},
        )
        return report

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self, organization_id: uuid.UUID) -> DatasetStats:
        p_count = (
            await self.session.execute(
                select(func.count(Participant.id)).where(
                    Participant.organization_id == organization_id,
                    Participant.is_active == True,
                )
            )
        ).scalar() or 0

        img_count = (
            await self.session.execute(
                select(func.count(ParticipantImage.id)).where(
                    ParticipantImage.organization_id == organization_id
                )
            )
        ).scalar() or 0

        indexed_count = (
            await self.session.execute(
                select(func.count(ParticipantImage.id)).where(
                    ParticipantImage.organization_id == organization_id,
                    ParticipantImage.index_status == ImageIndexStatus.INDEXED,
                )
            )
        ).scalar() or 0

        src_count = (
            await self.session.execute(
                select(func.count(ParticipantPublicSource.id)).where(
                    ParticipantPublicSource.organization_id == organization_id,
                    ParticipantPublicSource.participant_confirmed == True,
                )
            )
        ).scalar() or 0

        consent_pending = (
            await self.session.execute(
                select(func.count(Participant.id)).where(
                    Participant.organization_id == organization_id,
                    Participant.consent_status == ConsentStatus.PENDING,
                    Participant.is_active == True,
                )
            )
        ).scalar() or 0

        last_match_stmt = (
            select(DatasetMatch.matched_at)
            .where(DatasetMatch.organization_id == organization_id)
            .order_by(DatasetMatch.matched_at.desc())
            .limit(1)
        )
        last_match_at = (await self.session.execute(last_match_stmt)).scalar_one_or_none()

        return DatasetStats(
            participant_count=p_count,
            image_count=img_count,
            indexed_face_count=indexed_count,
            source_count=src_count,
            consent_pending_count=consent_pending,
            last_match_at=last_match_at,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _to_image_detail(self, pimg: ParticipantImage) -> ImageDetail:
        """Convert ParticipantImage to ImageDetail — NEVER includes storage_key."""
        return ImageDetail(
            id=pimg.id,
            participant_id=pimg.participant_id,
            mime_type=pimg.mime_type,
            file_size_bytes=pimg.file_size_bytes,
            width=pimg.width,
            height=pimg.height,
            sha256=pimg.sha256,
            phash=pimg.phash,
            dhash=pimg.dhash,
            aws_face_id=pimg.aws_face_id,
            aws_external_image_id=pimg.aws_external_image_id,
            index_status=pimg.index_status.value,
            index_error=pimg.index_error,
            aws_indexed_at=pimg.aws_indexed_at,
            face_confidence=pimg.face_confidence,
            image_sequence=pimg.image_sequence,
        )
