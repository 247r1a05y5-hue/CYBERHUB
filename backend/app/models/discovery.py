"""Discovery and Correlation models."""
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
    from app.models.dataset import DatasetIdentity
    from app.models.evidence import Evidence


class ConfidenceCategory(str, enum.Enum):
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MODERATE_CONFIDENCE = "MODERATE_CONFIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO_MATCH"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Match(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (
        Index("ix_matches_case_id", "case_id"),
        Index("ix_matches_identity_id", "dataset_identity_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_identities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_category: Mapped[ConfidenceCategory] = mapped_column(
        Enum(ConfidenceCategory, name="confidence_category"),
        nullable=False,
    )
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    signals_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="matches")
    dataset_identity: Mapped["DatasetIdentity"] = relationship("DatasetIdentity", back_populates="matches")

    def __repr__(self) -> str:
        return f"<Match id={self.id} score={self.similarity_score:.3f} conf={self.confidence_category}>"


class SearchJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "search_jobs"
    __table_args__ = (
        Index("ix_search_jobs_case_id", "case_id"),
        Index("ix_search_jobs_status", "status"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), default="GoogleCloudVisionWebDetection", nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.PENDING,
        nullable=False,
    )
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="search_jobs")
    results: Mapped[list["SearchResult"]] = relationship(
        "SearchResult", back_populates="search_job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SearchJob id={self.id} provider={self.provider} status={self.status}>"


class SearchResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "search_results"
    __table_args__ = (
        Index("ix_search_results_case_id", "case_id"),
        Index("ix_search_results_job_id", "search_job_id"),
        Index("ix_search_results_domain", "domain"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    search_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    page_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    page_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    similarity_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    result_type: Mapped[str] = mapped_column(String(50), default="EXACT_OR_SIMILAR", nullable=False)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="search_results")
    search_job: Mapped["SearchJob"] = relationship("SearchJob", back_populates="results")
    evidence: Mapped["Evidence | None"] = relationship("Evidence", back_populates="search_result", uselist=False)

    def __repr__(self) -> str:
        return f"<SearchResult id={self.id} domain={self.domain} score={self.similarity_score}>"


class CorrelationCluster(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "correlation_clusters"
    __table_args__ = (
        Index("ix_correlation_clusters_case_id", "case_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    cluster_name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    risk_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    domains_json: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="correlation_clusters")

    def __repr__(self) -> str:
        return f"<CorrelationCluster id={self.id} name={self.cluster_name} count={self.member_count}>"


class MatchCandidate(UUIDMixin, TimestampMixin, Base):
    """Calibrated Phase 3 match candidate persisted with tenant isolation."""
    __tablename__ = "match_candidates"
    __table_args__ = (
        Index("ix_match_candidates_investigation_id", "case_id"),
        Index("ix_match_candidates_org_id", "organization_id"),
        Index("ix_match_candidates_classification", "classification"),
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
    reference_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_images.id", ondelete="SET NULL"),
        nullable=True,
    )
    candidate_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    candidate_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier_applied: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    signals_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="match_candidates")

    def __init__(self, **kwargs):
        if "investigation_id" in kwargs and "case_id" not in kwargs:
            kwargs["case_id"] = kwargs.pop("investigation_id")
        super().__init__(**kwargs)

    @property
    def investigation_id(self) -> uuid.UUID:
        return self.case_id

    @investigation_id.setter
    def investigation_id(self, value: uuid.UUID) -> None:
        self.case_id = value

    def __repr__(self) -> str:
        return f"<MatchCandidate id={self.id} candidate={self.candidate_identifier} class={self.classification} score={self.similarity_score}>"

