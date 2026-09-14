"""Note — analyst notes attached to an incident."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.user import User


class Note(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_closing_note: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="notes")
    author: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Note id={self.id} incident={self.incident_id} closing={self.is_closing_note}>"
