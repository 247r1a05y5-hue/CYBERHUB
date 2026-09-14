"""Indicator — atomic observable (IP, domain, hash, URL, etc.)."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.organization import Organization


class IndicatorType(str, enum.Enum):
    ip_address = "ip_address"
    domain = "domain"
    url = "url"
    file_hash = "file_hash"
    email = "email"
    filename = "filename"
    registry_key = "registry_key"
    other = "other"


class Indicator(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "indicators"
    __table_args__ = (
        Index("ix_indicators_org_type", "organization_id", "indicator_type"),
        Index("ix_indicators_value", "value"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    indicator_type: Mapped[IndicatorType] = mapped_column(
        Enum(IndicatorType, name="indicator_type"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    analysis: Mapped["Analysis"] = relationship("Analysis")

    def __repr__(self) -> str:
        return f"<Indicator id={self.id} type={self.indicator_type} value={self.value[:32]}>"
