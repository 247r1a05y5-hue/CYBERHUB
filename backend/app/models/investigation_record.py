"""Phase 3 Investigation Models: Page Investigations, Candidate Images, Correlation, OCR, and Historical Snapshots.

All models enforce multi-tenant isolation via organization_id and case_id.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.discovery import SearchResult
    from app.models.organization import Organization


class CrawlStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    INACCESSIBLE = "INACCESSIBLE"
    BLOCKED = "BLOCKED"
    NO_PUBLIC_CONTENT = "NO_PUBLIC_CONTENT"
    ROBOTS_TXT_DISALLOWED = "ROBOTS_TXT_DISALLOWED"
    ERROR = "ERROR"


class FetchMethod(str, enum.Enum):
    HTTPX = "HTTPX"
    FIRECRAWL = "FIRECRAWL"
    BROWSERLESS = "BROWSERLESS"
    CACHE = "CACHE"


class HistoricalSource(str, enum.Enum):
    WAYBACK = "WAYBACK"
    COMMON_CRAWL = "COMMON_CRAWL"


class SnapshotStatus(str, enum.Enum):
    OBSERVED = "OBSERVED"
    NOT_OBSERVED = "NOT_OBSERVED"
    ERROR = "ERROR"


class PageInvestigation(UUIDMixin, TimestampMixin, Base):
    """Forensic record of a public webpage investigated during visual discovery."""
    __tablename__ = "page_investigations"
    __table_args__ = (
        Index("ix_page_inv_case_id", "case_id"),
        Index("ix_page_inv_org_id", "organization_id"),
        Index("ix_page_inv_search_result_id", "search_result_id"),
        Index("ix_page_inv_crawl_status", "crawl_status"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    search_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Forensic URL tracking (original vs final redirect destination)
    original_discovery_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    final_fetched_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # HTTP & Fetch metadata
    http_status: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    fetch_method: Mapped[FetchMethod] = mapped_column(
        Enum(FetchMethod, name="fetch_method"),
        default=FetchMethod.HTTPX,
        nullable=False,
    )
    fetch_provider: Mapped[str] = mapped_column(String(50), default="HTTPX", nullable=False)

    # Content extraction
    page_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    opengraph_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    twitter_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    visible_text_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_images_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status & Audit
    crawl_status: Mapped[CrawlStatus] = mapped_column(
        Enum(CrawlStatus, name="crawl_status"),
        default=CrawlStatus.SUCCESS,
        nullable=False,
    )
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    candidate_images: Mapped[list["CandidateImage"]] = relationship(
        "CandidateImage",
        back_populates="page_investigation",
        cascade="all, delete-orphan",
    )
    historical_snapshots: Mapped[list["HistoricalSnapshot"]] = relationship(
        "HistoricalSnapshot",
        back_populates="page_investigation",
        cascade="all, delete-orphan",
    )

    @property
    def investigation_id(self) -> uuid.UUID:
        """Alias for case_id to preserve compatibility with investigation endpoints."""
        return self.case_id

    @investigation_id.setter
    def investigation_id(self, value: uuid.UUID) -> None:
        self.case_id = value

    def __repr__(self) -> str:
        return f"<PageInvestigation id={self.id} url={self.final_fetched_url} status={self.crawl_status}>"


class CandidateImage(UUIDMixin, TimestampMixin, Base):
    """Candidate image extracted from an investigated page."""
    __tablename__ = "candidate_images"
    __table_args__ = (
        Index("ix_cand_img_case_id", "case_id"),
        Index("ix_cand_img_org_id", "organization_id"),
        Index("ix_cand_img_page_id", "page_investigation_id"),
        Index("ix_cand_img_sha256", "sha256_hash"),
    )

    page_investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("page_investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )

    original_image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    final_image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Cryptographic and perceptual hashes
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    phash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    dhash: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    # Image metadata
    mime_type: Mapped[str] = mapped_column(String(50), default="image/jpeg", nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Face detection metadata
    face_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_usable_face: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    page_investigation: Mapped["PageInvestigation"] = relationship(
        "PageInvestigation",
        back_populates="candidate_images",
    )
    correlations: Mapped[list["ImageCorrelation"]] = relationship(
        "ImageCorrelation",
        back_populates="candidate_image",
        cascade="all, delete-orphan",
    )
    ocr_extractions: Mapped[list["OcrExtraction"]] = relationship(
        "OcrExtraction",
        back_populates="candidate_image",
        cascade="all, delete-orphan",
    )
    historical_snapshots: Mapped[list["HistoricalSnapshot"]] = relationship(
        "HistoricalSnapshot",
        back_populates="candidate_image",
        cascade="all, delete-orphan",
    )

    @property
    def investigation_id(self) -> uuid.UUID:
        return self.case_id

    @investigation_id.setter
    def investigation_id(self, value: uuid.UUID) -> None:
        self.case_id = value

    def __repr__(self) -> str:
        return f"<CandidateImage id={self.id} sha256={self.sha256_hash[:10]} dim={self.width}x{self.height}>"


class ImageCorrelation(UUIDMixin, TimestampMixin, Base):
    """Multi-signal correlation result comparing reference image to candidate image."""
    __tablename__ = "image_correlations"
    __table_args__ = (
        Index("ix_img_corr_case_id", "case_id"),
        Index("ix_img_corr_org_id", "organization_id"),
        Index("ix_img_corr_cand_id", "candidate_image_id"),
        Index("ix_img_corr_classification", "classification"),
        Index("ix_img_corr_status", "status"),
    )

    candidate_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_images.id", ondelete="CASCADE"),
        nullable=False,
    )
    reference_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_images.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Classification & Similarity Metrics
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    dinov2_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    arcface_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    phash_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dhash_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Forensic audit and config reference (correlation_policy_v1.0)
    threshold_config_ref: Mapped[str] = mapped_column(String(100), default="correlation_policy_v1.0", nullable=False)
    model_info_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Status: Phase 3 stops strictly at PENDING_REVIEW (never VERIFIED)
    status: Mapped[str] = mapped_column(String(50), default="PENDING_REVIEW", nullable=False)

    # Relationships
    candidate_image: Mapped["CandidateImage"] = relationship(
        "CandidateImage",
        back_populates="correlations",
    )

    @property
    def investigation_id(self) -> uuid.UUID:
        return self.case_id

    @investigation_id.setter
    def investigation_id(self, value: uuid.UUID) -> None:
        self.case_id = value

    def __repr__(self) -> str:
        return f"<ImageCorrelation id={self.id} class={self.classification} status={self.status}>"


class OcrExtraction(UUIDMixin, TimestampMixin, Base):
    """OCR text, handles, watermarks, and labels extracted from a candidate image."""
    __tablename__ = "ocr_extractions"
    __table_args__ = (
        Index("ix_ocr_cand_id", "candidate_image_id"),
        Index("ix_ocr_org_id", "organization_id"),
    )

    candidate_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_images.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    extracted_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    engine_name: Mapped[str] = mapped_column(String(50), default="Tesseract-OCR", nullable=False)
    engine_version: Mapped[str] = mapped_column(String(50), default="5.x / pytesseract", nullable=False)
    detected_entities_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    candidate_image: Mapped["CandidateImage"] = relationship(
        "CandidateImage",
        back_populates="ocr_extractions",
    )

    def __repr__(self) -> str:
        return f"<OcrExtraction id={self.id} engine={self.engine_name} chars={len(self.extracted_text)}>"


class HistoricalSnapshot(UUIDMixin, TimestampMixin, Base):
    """Archival capture record from Wayback Machine or Common Crawl."""
    __tablename__ = "historical_snapshots"
    __table_args__ = (
        Index("ix_hist_page_id", "page_investigation_id"),
        Index("ix_hist_cand_id", "candidate_image_id"),
        Index("ix_hist_source", "source"),
        Index("ix_hist_status", "status"),
    )

    page_investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("page_investigations.id", ondelete="CASCADE"),
        nullable=True,
    )
    candidate_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_images.id", ondelete="CASCADE"),
        nullable=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    source: Mapped[HistoricalSource] = mapped_column(
        Enum(HistoricalSource, name="historical_source"),
        nullable=False,
    )
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    capture_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archive_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Semantics: NOT_OBSERVED preserves uncertainty (never asserts "never existed")
    status: Mapped[SnapshotStatus] = mapped_column(
        Enum(SnapshotStatus, name="snapshot_status"),
        default=SnapshotStatus.NOT_OBSERVED,
        nullable=False,
    )
    digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    page_investigation: Mapped["PageInvestigation | None"] = relationship(
        "PageInvestigation",
        back_populates="historical_snapshots",
    )
    candidate_image: Mapped["CandidateImage | None"] = relationship(
        "CandidateImage",
        back_populates="historical_snapshots",
    )

    def __repr__(self) -> str:
        return f"<HistoricalSnapshot id={self.id} source={self.source} status={self.status}>"
