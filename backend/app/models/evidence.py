"""Evidence and Chain-of-Custody models — Append-only, immutable."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.discovery import SearchResult


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNCERTAIN = "UNCERTAIN"


class EvidenceType(str, enum.Enum):
    REFERENCE_IMAGE = "REFERENCE_IMAGE"
    DISCOVERED_IMAGE = "DISCOVERED_IMAGE"
    SOURCE_PAGE = "SOURCE_PAGE"
    SCREENSHOT = "SCREENSHOT"
    PAGE_METADATA = "PAGE_METADATA"
    MATCH_METADATA = "MATCH_METADATA"
    PROVIDER_RESULT = "PROVIDER_RESULT"
    ANALYST_NOTE = "ANALYST_NOTE"
    HASH_MANIFEST = "HASH_MANIFEST"
    REPORT_ARTIFACT = "REPORT_ARTIFACT"
    WEB_SCREENSHOT = "WEB_SCREENSHOT"
    IMAGE_FILE = "IMAGE_FILE"
    IMAGE = "IMAGE"
    METADATA_BUNDLE = "METADATA_BUNDLE"
    RAW_HTML = "RAW_HTML"


class Evidence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evidence_vault"
    __table_args__ = (
        Index("ix_evidence_case_id", "case_id"),
        Index("ix_evidence_status", "verification_status"),
        Index("ix_evidence_sha256", "sha256_hash"),
        Index("ix_evidence_custody_seq", "case_id", "custody_sequence"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    search_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    evidence_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    custody_sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    previous_evidence_hash: Mapped[str] = mapped_column(
        String(64), default="GENESIS_EVIDENCE_ROOT", nullable=False
    )
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    page_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    page_title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    content_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream", nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    collection_method: Mapped[str] = mapped_column(String(100), default="AUTOMATED_CAPTURE", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="GoogleCloudVision", nullable=False)
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, name="evidence_type"),
        default=EvidenceType.DISCOVERED_IMAGE,
        nullable=False,
    )

    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        default=VerificationStatus.UNVERIFIED,
        nullable=False,
    )
    user_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chain_of_custody_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="evidence_items")
    search_result: Mapped["SearchResult | None"] = relationship("SearchResult", back_populates="evidence")
    events: Mapped[list["EvidenceEvent"]] = relationship(
        "EvidenceEvent", back_populates="evidence", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Evidence num={self.evidence_number} domain={self.domain} status={self.verification_status}>"


class EvidenceEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evidence_events"
    __table_args__ = (
        Index("ix_evidence_events_case_id", "case_id"),
        Index("ix_evidence_events_evidence_id", "evidence_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_vault.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="evidence_events")
    evidence: Mapped["Evidence"] = relationship("Evidence", back_populates="events")

    def __repr__(self) -> str:
        return f"<EvidenceEvent id={self.id} type={self.event_type}>"
