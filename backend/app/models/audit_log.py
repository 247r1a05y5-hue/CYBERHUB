"""AuditLog — immutable append-only event record. NEVER logs secrets."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class AuditAction(str, enum.Enum):
    # Auth
    user_registered = "user_registered"
    user_login = "user_login"
    user_logout = "user_logout"
    token_refreshed = "token_refreshed"
    login_failed = "login_failed"
    # User management
    user_created = "user_created"
    user_updated = "user_updated"
    user_role_changed = "user_role_changed"
    user_deactivated = "user_deactivated"
    # CyberHub Case lifecycle
    case_created = "case_created"
    case_updated = "case_updated"
    face_validated = "face_validated"
    dataset_searched = "dataset_searched"
    identity_confirmed = "identity_confirmed"
    dataset_enrolled = "dataset_enrolled"
    discovery_started = "discovery_started"
    discovery_provider_called = "discovery_provider_called"
    discovery_dedup_completed = "discovery_dedup_completed"
    discovery_completed = "discovery_completed"
    discovery_failed = "discovery_failed"
    result_verified = "result_verified"
    evidence_preserved = "evidence_preserved"
    evidence_exported = "evidence_exported"
    risk_calculated = "risk_calculated"
    report_generated = "report_generated"
    complaint_drafted = "complaint_drafted"
    complaint_reviewed = "complaint_reviewed"
    monitoring_updated = "monitoring_updated"
    # Analysis & Alert legacy
    analysis_created = "analysis_created"
    analysis_completed = "analysis_completed"
    alert_created = "alert_created"
    # Phase 3 Web Investigation, Correlation & Context Actions
    page_investigation_started = "page_investigation_started"
    page_investigation_completed = "page_investigation_completed"
    rendering_fallback_escalated = "rendering_fallback_escalated"
    candidate_image_downloaded = "candidate_image_downloaded"
    image_correlation_evaluated = "image_correlation_evaluated"
    ocr_extraction_completed = "ocr_extraction_completed"
    historical_lookup_completed = "historical_lookup_completed"
    # Phase 5 Evidence, Risk, Report, Response actions
    evidence_viewed = "evidence_viewed"
    evidence_downloaded = "evidence_downloaded"
    evidence_manifest_exported = "evidence_manifest_exported"
    evidence_integrity_verified = "evidence_integrity_verified"
    risk_recalculated = "risk_recalculated"
    report_queued = "report_queued"
    report_downloaded = "report_downloaded"
    response_package_generated = "response_package_generated"
    response_package_downloaded = "response_package_downloaded"
    # Generic actions
    create = "create"
    update = "update"
    delete = "delete"
    read = "read"
    export = "export"
    # Admin
    organization_created = "organization_created"
    admin_action = "admin_action"


class AuditLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_org_action", "organization_id", "action"),
        Index("ix_audit_logs_user", "user_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"), nullable=False, index=True
    )
    # What resource was acted upon
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Non-sensitive context only — NEVER passwords, tokens, hashes
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Network context for forensics
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="audit_logs"
    )
    user: Mapped["User"] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} user={self.user_id}>"
