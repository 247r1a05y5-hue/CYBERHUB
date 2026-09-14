"""IncidentAlert — many-to-many join between incidents and alerts."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.alert import Alert


class IncidentAlert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "incident_alerts"
    __table_args__ = (
        UniqueConstraint("incident_id", "alert_id", name="uq_incident_alert"),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="alert_links")
    alert: Mapped["Alert"] = relationship("Alert", back_populates="incident_links")

    def __repr__(self) -> str:
        return f"<IncidentAlert incident={self.incident_id} alert={self.alert_id}>"
