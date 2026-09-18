"""Participant models for controlled-dataset AWS Rekognition pipeline.

Privacy rule (enforced at the API layer): stored image URLs / storage keys /
raw face images MUST NEVER appear in any HTTP response — only participant
metadata and participant-confirmed public source URLs are returned.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConsentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONSENTED = "CONSENTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ImageIndexStatus(str, enum.Enum):
    PENDING = "PENDING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class MatchStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNCERTAIN = "UNCERTAIN"


class VerificationStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNCERTAIN = "UNCERTAIN"


# ---------------------------------------------------------------------------
# Participant — the enrolled person
# ---------------------------------------------------------------------------


class Participant(UUIDMixin, TimestampMixin, Base):
    """An enrolled person in the controlled dataset.

    Immutable invariant: a participant with consent_status != CONSENTED
    must never have their images indexed into AWS Rekognition.
    """

    __tablename__ = "participants"
    __table_args__ = (
        Index("ix_participants_org_id", "organization_id"),
        Index("ix_participants_org_code", "organization_id", "participant_code"),
        UniqueConstraint("organization_id", "participant_code", name="uq_participant_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_code: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aws_collection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent_status: Mapped[ConsentStatus] = mapped_column(
        Enum(ConsentStatus, name="consent_status"),
        nullable=False,
        default=ConsentStatus.PENDING,
    )
    consent_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    images: Mapped[list["ParticipantImage"]] = relationship(
        "ParticipantImage", back_populates="participant", cascade="all, delete-orphan"
    )
    public_sources: Mapped[list["ParticipantPublicSource"]] = relationship(
        "ParticipantPublicSource", back_populates="participant", cascade="all, delete-orphan"
    )
    consents: Mapped[list["ParticipantConsent"]] = relationship(
        "ParticipantConsent", back_populates="participant", cascade="all, delete-orphan"
    )
    matches: Mapped[list["DatasetMatch"]] = relationship(
        "DatasetMatch", back_populates="participant"
    )

    def __repr__(self) -> str:
        return f"<Participant id={self.id} code={self.participant_code} consent={self.consent_status}>"


# ---------------------------------------------------------------------------
# ParticipantImage — stored securely, NEVER returned in API responses
# ---------------------------------------------------------------------------


class ParticipantImage(UUIDMixin, TimestampMixin, Base):
    """One authorized photograph of a participant.

    The storage_key and all path fields MUST NEVER appear in any HTTP
    response body — enforced by the API schema (no storage_key field).
    """

    __tablename__ = "participant_images"
    __table_args__ = (
        Index("ix_participant_images_participant_id", "participant_id"),
        Index("ix_participant_images_org_id", "organization_id"),
        Index("ix_participant_images_sha256", "sha256"),
        Index("ix_participant_images_aws_face_id", "aws_face_id"),
        UniqueConstraint("organization_id", "sha256", name="uq_participant_image_org_sha256"),
    )

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Perceptual hashes for local secondary verification
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    phash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dhash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Storage — NEVER exposed in API responses
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # AWS Rekognition fields
    aws_face_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aws_external_image_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aws_collection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aws_indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    face_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    index_status: Mapped[ImageIndexStatus] = mapped_column(
        Enum(ImageIndexStatus, name="image_index_status"),
        nullable=False,
        default=ImageIndexStatus.PENDING,
    )
    index_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    participant: Mapped["Participant"] = relationship("Participant", back_populates="images")

    def __repr__(self) -> str:
        return f"<ParticipantImage id={self.id} participant={self.participant_id} status={self.index_status}>"


# ---------------------------------------------------------------------------
# ParticipantPublicSource — the ONLY URLs returned in match responses
# ---------------------------------------------------------------------------


class ParticipantPublicSource(UUIDMixin, TimestampMixin, Base):
    """A participant-confirmed public URL (e.g. Instagram, LinkedIn).

    Only rows with participant_confirmed=True are returned in match responses.
    URLs are returned exactly as stored — never guessed, constructed, or scraped.
    """

    __tablename__ = "participant_public_sources"
    __table_args__ = (
        Index("ix_pps_participant_id", "participant_id"),
        Index("ix_pps_org_id", "organization_id"),
        UniqueConstraint("participant_id", "url", name="uq_pps_participant_url"),
    )

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(100), nullable=False)  # instagram, linkedin, etc.
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    participant_confirmed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    participant: Mapped["Participant"] = relationship("Participant", back_populates="public_sources")

    def __repr__(self) -> str:
        return f"<ParticipantPublicSource id={self.id} platform={self.platform} confirmed={self.participant_confirmed}>"


# ---------------------------------------------------------------------------
# ParticipantConsent — consent audit trail
# ---------------------------------------------------------------------------


class ParticipantConsent(UUIDMixin, TimestampMixin, Base):
    """Consent record for a participant."""

    __tablename__ = "participant_consents"
    __table_args__ = (
        Index("ix_participant_consents_participant_id", "participant_id"),
    )

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    consent_status: Mapped[ConsentStatus] = mapped_column(
        Enum(ConsentStatus, name="consent_status", create_constraint=False),
        nullable=False,
    )
    consent_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    consent_method: Mapped[str] = mapped_column(
        String(100), default="ADMIN_ENROLLMENT", nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    participant: Mapped["Participant"] = relationship("Participant", back_populates="consents")

    def __repr__(self) -> str:
        return f"<ParticipantConsent id={self.id} status={self.consent_status}>"


# ---------------------------------------------------------------------------
# DatasetMatch — one camera-match event
# ---------------------------------------------------------------------------


class DatasetMatch(UUIDMixin, TimestampMixin, Base):
    """Records the result of one SearchFacesByImage call against the dataset."""

    __tablename__ = "dataset_matches"
    __table_args__ = (
        Index("ix_dataset_matches_org_id", "organization_id"),
        Index("ix_dataset_matches_participant_id", "participant_id"),
        Index("ix_dataset_matches_status", "match_status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Optional — if the match was triggered inside an investigation case
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Query image fingerprint (never the raw bytes or file path)
    query_image_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    query_image_phash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # AWS result
    aws_face_id_matched: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aws_external_image_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aws_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    aws_collection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Local secondary verification (pHash/dHash — kept separate, never blended)
    local_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    local_match_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Status
    match_status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status"),
        nullable=False,
        default=MatchStatus.PENDING_REVIEW,
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    participant: Mapped["Participant | None"] = relationship("Participant", back_populates="matches")
    verifications: Mapped[list["DatasetVerification"]] = relationship(
        "DatasetVerification", back_populates="match", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DatasetMatch id={self.id} status={self.match_status} aws_sim={self.aws_similarity}>"


# ---------------------------------------------------------------------------
# DatasetVerification — human review of a match
# ---------------------------------------------------------------------------


class DatasetVerification(UUIDMixin, TimestampMixin, Base):
    """Human verification decision on a DatasetMatch."""

    __tablename__ = "dataset_verifications"
    __table_args__ = (
        Index("ix_dataset_verifications_match_id", "match_id"),
        Index("ix_dataset_verifications_org_id", "organization_id"),
    )

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        nullable=False,
        default=VerificationStatus.PENDING_REVIEW,
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    match: Mapped["DatasetMatch"] = relationship("DatasetMatch", back_populates="verifications")

    def __repr__(self) -> str:
        return f"<DatasetVerification id={self.id} status={self.status}>"
