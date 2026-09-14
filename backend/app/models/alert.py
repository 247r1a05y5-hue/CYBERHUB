"""Alert model — actionable security alert with deduplication."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.analysis_result import Severity

AlertSeverity = Severity


if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.analysis import Analysis
    from app.models.incident_alert import IncidentAlert


class AlertStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    false_positive = "false_positive"
    escalated = "escalated"
    resolved = "resolved"


class Alert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_org_status", "organization_id", "status"),
        Index("ix_alerts_dedup_key", "dedup_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), nullable=False, index=True
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"),
        nullable=False,
        default=AlertStatus.open,
        index=True,
    )

    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Deterministic dedup key — same analysis type + content hash → same key
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="alerts")
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="alerts")
    assigned_to: Mapped["User"] = relationship(
        "User", back_populates="assigned_alerts", foreign_keys=[assigned_to_id]
    )
    incident_links: Mapped[list["IncidentAlert"]] = relationship(
        "IncidentAlert", back_populates="alert"
    )

    def __repr__(self) -> str:
        return f"<Alert id={self.id} severity={self.severity} status={self.status}>"
