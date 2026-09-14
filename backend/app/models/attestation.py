"""Attestation model for legal / policy audit controls.

IMPORTANT:
This attestation is a logged policy and audit control.
It is NOT technical proof of ownership or authorization,
and is NOT a cryptographic signature.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.organization import Organization
    from app.models.user import User


class InvestigationAttestation(UUIDMixin, TimestampMixin, Base):
    """Audit record capturing user authorization attestation for an investigation."""
    __tablename__ = "investigation_attestations"
    __table_args__ = (
        Index("ix_attestations_case_id", "case_id"),
        Index("ix_attestations_org_id", "organization_id"),
        Index("ix_attestations_user_id", "user_id"),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    attestation_text: Mapped[str] = mapped_column(Text, nullable=False)
    attestation_version: Mapped[str] = mapped_column(String(50), default="v1.0.0", nullable=False)
    reference_image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    case: Mapped["Case"] = relationship("Case")
    organization: Mapped["Organization"] = relationship("Organization")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<InvestigationAttestation id={self.id} case_id={self.case_id} hash={self.reference_image_hash[:8]}>"
