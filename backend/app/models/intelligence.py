"""Intelligence models — Risk assessment, reports, complaints, monitoring rules, timeline."""
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


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReportFormat(str, enum.Enum):
    PDF = "PDF"
    JSON = "JSON"
    CSV = "CSV"
    ZIP = "ZIP"
    TEXT = "TEXT"


class ReportStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ComplaintStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    EXPORTED = "EXPORTED"


class RiskAssessment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        Index("ix_risk_assessments_case_id", "case_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_policy_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    overall_risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level"),
        default=RiskLevel.MEDIUM,
        nullable=False,
    )
    calculated_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    factor_breakdown_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    risk_factors_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)
    verified_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unverified_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assessed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="risk_assessments")

    def __repr__(self) -> str:
        return f"<RiskAssessment id={self.id} level={self.overall_risk_level} score={self.calculated_score}>"


class CaseReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "case_reports"
    __table_args__ = (
        Index("ix_case_reports_case_id", "case_id"),
        Index("ix_case_reports_status", "status"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_format: Mapped[ReportFormat] = mapped_column(
        Enum(ReportFormat, name="report_format"),
        default=ReportFormat.PDF,
        nullable=False,
    )
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"),
        default=ReportStatus.COMPLETED,
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="reports")

    def __repr__(self) -> str:
        return f"<CaseReport id={self.id} title={self.report_title} format={self.report_format} status={self.status}>"


Report = CaseReport


class ResponsePackage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "response_packages"
    __table_args__ = (
        Index("ix_response_packages_case_id", "case_id"),
        Index("ix_response_packages_number", "package_number"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    package_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    target_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(255), nullable=False)
    incident_summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_manifest_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    takedown_letter_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    contact_channels_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    package_format: Mapped[str] = mapped_column(String(20), default="MARKDOWN", nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="READY", nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="response_packages")

    def __repr__(self) -> str:
        return f"<ResponsePackage num={self.package_number} domain={self.target_domain} status={self.status}>"


class Complaint(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "complaints"
    __table_args__ = (
        Index("ix_complaints_case_id", "case_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_entity: Mapped[str] = mapped_column(String(255), nullable=False)
    incident_summary: Mapped[str] = mapped_column(Text, nullable=False)
    draft_body: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids_json: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaint_status"),
        default=ComplaintStatus.DRAFT,
        nullable=False,
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="complaints")

    def __repr__(self) -> str:
        return f"<Complaint id={self.id} target={self.target_entity} status={self.status}>"


class MonitoringRule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "monitoring_rules"
    __table_args__ = (
        Index("ix_monitoring_rules_case_id", "case_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_name: Mapped[str] = mapped_column(String(255), default="Exposure Monitoring", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="GoogleCloudVision,TinEye", nullable=False)
    frequency: Mapped[str] = mapped_column(String(50), default="DAILY", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_status: Mapped[str] = mapped_column(String(50), default="IDLE", nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    previous_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_delta_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="monitoring_rules")
    runs: Mapped[list["MonitoringRun"]] = relationship("MonitoringRun", back_populates="rule", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MonitoringRule id={self.id} enabled={self.enabled} delta={self.new_delta_count}>"


class MonitoringRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "monitoring_runs"
    __table_args__ = (
        Index("ix_monitoring_runs_rule_id", "rule_id"),
        Index("ix_monitoring_runs_case_id", "case_id"),
        Index("ix_monitoring_runs_created_at", "created_at"),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitoring_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)
    provider_status: Mapped[str] = mapped_column(String(50), default="READY", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_observed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reappeared_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_new_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[dict | list] = mapped_column(JSONB, default=dict, nullable=False)

    rule: Mapped["MonitoringRule"] = relationship("MonitoringRule", back_populates="runs")
    case: Mapped["Case"] = relationship("Case")

    def __repr__(self) -> str:
        return f"<MonitoringRun id={self.id} status={self.status} new={self.new_count} not_observed={self.not_observed_count}>"


class TimelineEvent(UUIDMixin, TimestampMixin, Base):

    __tablename__ = "timeline_events"
    __table_args__ = (
        Index("ix_timeline_events_case_id", "case_id"),
        Index("ix_timeline_events_created_at", "created_at"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="timeline_events")

    def __repr__(self) -> str:
        return f"<TimelineEvent id={self.id} type={self.event_type} title={self.title}>"
