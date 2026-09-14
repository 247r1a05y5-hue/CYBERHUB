"""AnalysisResult — persisted output from the full analysis pipeline."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class Verdict(str, enum.Enum):
    benign = "benign"
    suspicious = "suspicious"
    malicious = "malicious"
    unknown = "unknown"


class Severity(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AnalysisResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analysis_results"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    verdict: Mapped[Verdict] = mapped_column(
        Enum(Verdict, name="verdict"), nullable=False, index=True
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), nullable=False, index=True
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Human-readable summary
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured detail — stored as JSONB for flexibility
    reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    contributing_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    recommendations: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    indicators: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    # Model and rule metadata
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_pack_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Raw pipeline outputs (for debugging and audit — never exposed to client directly)
    raw_findings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="result")

    def __repr__(self) -> str:
        return (
            f"<AnalysisResult id={self.id} verdict={self.verdict} score={self.risk_score}>"
        )
