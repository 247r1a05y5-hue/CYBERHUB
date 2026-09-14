"""Organization model — top-level tenant boundary."""
from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.analysis import Analysis
    from app.models.alert import Alert
    from app.models.incident import Incident
    from app.models.report import Report
    from app.models.audit_log import AuditLog


def _slugify(name: str) -> str:
    """Convert a name to a URL-safe slug with a UUID suffix for uniqueness."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
    suffix = uuid.uuid4().hex[:8]
    return f"{base}-{suffix}"


class Organization(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    analyses: Mapped[list["Analysis"]] = relationship("Analysis", back_populates="organization")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="organization")
    incidents: Mapped[list["Incident"]] = relationship("Incident", back_populates="organization")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="organization")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="organization")

    def __init__(self, **kwargs: object) -> None:
        if "slug" not in kwargs or kwargs["slug"] is None:
            kwargs["slug"] = _slugify(str(kwargs.get("name", "org")))
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug}>"
