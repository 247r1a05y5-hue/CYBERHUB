"""AnalysisInput — raw (sanitized) input stored separately from the job record."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class InputType(str, enum.Enum):
    text = "text"
    file = "file"
    url = "url"
    mock = "mock"


class AnalysisInput(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analysis_inputs"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    input_type: Mapped[InputType] = mapped_column(
        Enum(InputType, name="input_type"), nullable=False
    )
    # Text/URL content (if applicable)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # File reference — UUID filename in storage (never the original filename)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="input")

    def __init__(self, **kwargs):
        if "storage_ref" in kwargs and "storage_path" not in kwargs:
            kwargs["storage_path"] = kwargs.pop("storage_ref")
        self.raw_metadata = kwargs.pop("raw_metadata", None)
        super().__init__(**kwargs)

    @property
    def storage_ref(self) -> str | None:
        return self.storage_path

    @storage_ref.setter
    def storage_ref(self, value: str | None) -> None:
        self.storage_path = value

    def __repr__(self) -> str:
        return f"<AnalysisInput id={self.id} type={self.input_type}>"
