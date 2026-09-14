"""Case model for CyberHub investigation lifecycle."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.biometrics import ReferenceImage, FaceRecord
    from app.models.discovery import SearchJob, SearchResult, Match, MatchCandidate, CorrelationCluster
    from app.models.evidence import Evidence, EvidenceEvent
    from app.models.intelligence import RiskAssessment, Report, Complaint, MonitoringRule, TimelineEvent, ResponsePackage


class CaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CAPTURED = "CAPTURED"
    VALIDATED = "VALIDATED"
    MATCH_CONFIRMED = "MATCH_CONFIRMED"
    DISCOVERY_RUNNING = "DISCOVERY_RUNNING"
    DISCOVERY_COMPLETE = "DISCOVERY_COMPLETE"
    AWAITING_VERIFICATION = "AWAITING_VERIFICATION"
    VERIFIED = "VERIFIED"
    EVIDENCE_READY = "EVIDENCE_READY"
    RISK_ASSESSED = "RISK_ASSESSED"
    REPORT_READY = "REPORT_READY"
    MONITORING_ACTIVE = "MONITORING_ACTIVE"
    CLOSED = "CLOSED"


class CaseStage(int, enum.Enum):
    CAPTURE = 1
    MATCH = 2
    DISCOVERY = 3
    CORRELATION = 4
    VERIFICATION = 5
    EVIDENCE = 6
    RISK = 7
    REPORT = 8
    MONITORING = 9


class Case(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_org_status", "organization_id", "status"),
        Index("ix_cases_created_by", "created_by_id"),
        Index("ix_cases_created_at", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    case_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_subject_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status"),
        nullable=False,
        default=CaseStatus.DRAFT,
        index=True,
    )
    current_stage: Mapped[int] = mapped_column(default=1, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    created_by: Mapped["User"] = relationship("User")

    def __init__(self, **kwargs):
        if "created_by" in kwargs and isinstance(kwargs["created_by"], (uuid.UUID, str)):
            val = kwargs.pop("created_by")
            kwargs["created_by_id"] = val if isinstance(val, uuid.UUID) else uuid.UUID(str(val))
        if "case_number" not in kwargs:
            kwargs["case_number"] = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        super().__init__(**kwargs)

    reference_images: Mapped[list["ReferenceImage"]] = relationship(
        "ReferenceImage", back_populates="case", cascade="all, delete-orphan"
    )
    face_records: Mapped[list["FaceRecord"]] = relationship(
        "FaceRecord", back_populates="case", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="case", cascade="all, delete-orphan"
    )
    match_candidates: Mapped[list["MatchCandidate"]] = relationship(
        "MatchCandidate", back_populates="case", cascade="all, delete-orphan"
    )
    search_jobs: Mapped[list["SearchJob"]] = relationship(
        "SearchJob", back_populates="case", cascade="all, delete-orphan"
    )
    search_results: Mapped[list["SearchResult"]] = relationship(
        "SearchResult", back_populates="case", cascade="all, delete-orphan"
    )
    correlation_clusters: Mapped[list["CorrelationCluster"]] = relationship(
        "CorrelationCluster", back_populates="case", cascade="all, delete-orphan"
    )
    evidence_items: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="case", cascade="all, delete-orphan"
    )
    evidence_events: Mapped[list["EvidenceEvent"]] = relationship(
        "EvidenceEvent", back_populates="case", cascade="all, delete-orphan"
    )
    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(
        "RiskAssessment", back_populates="case", cascade="all, delete-orphan"
    )
    reports: Mapped[list["CaseReport"]] = relationship(
        "CaseReport", back_populates="case", cascade="all, delete-orphan"
    )
    complaints: Mapped[list["Complaint"]] = relationship(
        "Complaint", back_populates="case", cascade="all, delete-orphan"
    )
    response_packages: Mapped[list["ResponsePackage"]] = relationship(
        "ResponsePackage", back_populates="case", cascade="all, delete-orphan"
    )
    monitoring_rules: Mapped[list["MonitoringRule"]] = relationship(
        "MonitoringRule", back_populates="case", cascade="all, delete-orphan"
    )
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(
        "TimelineEvent", back_populates="case", cascade="all, delete-orphan", order_by="TimelineEvent.created_at"
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} number={self.case_number} status={self.status}>"
