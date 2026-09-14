"""Analysis model — one analysis job lifecycle record."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.analysis_input import AnalysisInput
    from app.models.analysis_result import AnalysisResult
    from app.models.alert import Alert
    from app.models.evidence import Evidence


class AnalysisStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AnalysisType(str, enum.Enum):
    mock = "mock"
    # Future: phishing, malware, deepfake, etc.


class Analysis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("ix_analyses_org_status", "organization_id", "status"),
        Index("ix_analyses_org_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    analyzer_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        nullable=False,
        default=AnalysisStatus.queued,
        index=True,
    )
    # SHA-256 of the input content — used for idempotency
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # RQ job id for tracking
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Tags for search/filter
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="analyses"
    )
    created_by: Mapped["User"] = relationship("User", back_populates="analyses")
    input: Mapped["AnalysisInput"] = relationship(
        "AnalysisInput", back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )
    result: Mapped["AnalysisResult"] = relationship(
        "AnalysisResult", back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} type={self.analyzer_type} status={self.status}>"
