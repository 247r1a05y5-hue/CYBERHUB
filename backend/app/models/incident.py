"""Incident model — full FSM with strict transition map."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.analysis_result import Severity

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.incident_alert import IncidentAlert
    from app.models.note import Note
    from app.models.evidence import Evidence


class IncidentStatus(str, enum.Enum):
    new = "new"
    triaged = "triaged"
    investigating = "investigating"
    containment = "containment"
    mitigation = "mitigation"
    resolved = "resolved"
    closed = "closed"


# Explicit transition map — enforced in the service layer
INCIDENT_TRANSITIONS: dict[IncidentStatus, list[IncidentStatus]] = {
    IncidentStatus.new: [IncidentStatus.triaged],
    IncidentStatus.triaged: [IncidentStatus.investigating],
    IncidentStatus.investigating: [IncidentStatus.containment, IncidentStatus.resolved],
    IncidentStatus.containment: [IncidentStatus.mitigation],
    IncidentStatus.mitigation: [IncidentStatus.resolved],
    IncidentStatus.resolved: [IncidentStatus.closed],
    IncidentStatus.closed: [],  # terminal
}

# These statuses require a closing note
STATUSES_REQUIRING_NOTE = {IncidentStatus.resolved, IncidentStatus.closed}


class Incident(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"),
        nullable=False,
        default=IncidentStatus.new,
        index=True,
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), nullable=False
    )

    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="incidents"
    )
    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_incidents", foreign_keys=[owner_id]
    )
    alert_links: Mapped[list["IncidentAlert"]] = relationship(
        "IncidentAlert", back_populates="incident", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="incident", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Incident id={self.id} status={self.status} severity={self.severity}>"
