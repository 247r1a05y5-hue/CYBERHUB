"""Biometric models — Reference images, face detection records, and embeddings."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.case import Case


class FaceValidationStatus(str, enum.Enum):
    PENDING = "PENDING"
    NO_FACE = "NO_FACE"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    POOR_QUALITY = "POOR_QUALITY"
    VALID = "VALID"
    PROCESSED = "PROCESSED"


class ReferenceImage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reference_images"
    __table_args__ = (
        Index("ix_reference_images_case_id", "case_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="image/jpeg", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="reference_images")
    face_records: Mapped[list["FaceRecord"]] = relationship(
        "FaceRecord", back_populates="reference_image", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        if "storage_path" in kwargs and "file_path" not in kwargs:
            kwargs["file_path"] = kwargs.pop("storage_path")
        if "image_url" not in kwargs:
            kwargs["image_url"] = f"/api/v1/investigations/{kwargs.get('case_id')}/reference-image/raw"
        self.organization_id = kwargs.pop("organization_id", None)
        self.file_name = kwargs.pop("file_name", None)
        self.uploaded_by = kwargs.pop("uploaded_by", None)
        self.phash = kwargs.pop("phash", None)
        self.dhash = kwargs.pop("dhash", None)
        super().__init__(**kwargs)

    @property
    def storage_path(self) -> str | None:
        return self.file_path

    @storage_path.setter
    def storage_path(self, value: str | None) -> None:
        self.file_path = value

    def __repr__(self) -> str:
        return f"<ReferenceImage id={self.id} hash={self.sha256_hash[:8]}>"


class FaceRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "face_records"
    __table_args__ = (
        Index("ix_face_records_case_id", "case_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    reference_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_images.id", ondelete="CASCADE"),
        nullable=False,
    )
    bounding_box: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    landmarks: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    face_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_status: Mapped[FaceValidationStatus] = mapped_column(
        Enum(FaceValidationStatus, name="face_validation_status"),
        default=FaceValidationStatus.PENDING,
        nullable=False,
    )

    case: Mapped["Case"] = relationship("Case", back_populates="face_records")
    reference_image: Mapped["ReferenceImage"] = relationship("ReferenceImage", back_populates="face_records")
    embeddings: Mapped[list["FaceEmbedding"]] = relationship(
        "FaceEmbedding", back_populates="face_record", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FaceRecord id={self.id} status={self.validation_status} valid={self.is_valid}>"


class FaceEmbedding(UUIDMixin, TimestampMixin, Base):
    """Raw vector embedding storage — NEVER serialized to API responses or logs."""
    __tablename__ = "face_embeddings"

    face_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("face_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vector_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    algorithm: Mapped[str] = mapped_column(String(50), default="ArcFace-r100", nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=512, nullable=False)

    face_record: Mapped["FaceRecord"] = relationship("FaceRecord", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<FaceEmbedding id={self.id} algo={self.algorithm}>"
