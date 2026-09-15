"""Top-level v1 API router registering all domain sub-routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.alerts import router as alerts_router
from app.api.v1.endpoints.analyses import router as analyses_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cases import router as cases_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.datasets import router as datasets_router
from app.api.v1.endpoints.diagnostics import router as diagnostics_router
from app.api.v1.endpoints.evidence import router as evidence_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.image_investigations import router as image_investigations_router
from app.api.v1.endpoints.incidents import router as incidents_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.organizations import router as organizations_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.stream import router as stream_router
from app.api.v1.endpoints.temp_images import router as temp_images_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()

# System & Search Diagnostics
api_router.include_router(diagnostics_router, prefix="/system/diagnostics", tags=["diagnostics"])
api_router.include_router(diagnostics_router, prefix="/diagnostics", tags=["diagnostics"])

# Ephemeral Temporary Images (For External SearchAPI Google Lens Crawlers)
api_router.include_router(temp_images_router, prefix="/temp-images", tags=["temp-images"])

# Health
api_router.include_router(health_router, prefix="/health", tags=["health"])

# Auth & Identity
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(organizations_router, prefix="/organizations", tags=["organizations"])
api_router.include_router(users_router, prefix="/users", tags=["users"])

# CyberHub Case Lifecycle & Bounded Datasets
api_router.include_router(cases_router, prefix="/cases", tags=["cases"])
api_router.include_router(datasets_router, prefix="/datasets", tags=["datasets"])

# Image Exposure Investigation (Strict Image-to-Image Pipeline)
api_router.include_router(image_investigations_router, prefix="/investigations", tags=["investigations"])

# Analysis Pipeline & Real-Time Stream
api_router.include_router(analyses_router, prefix="/analyses", tags=["analyses"])
api_router.include_router(stream_router, tags=["stream"])

# Operations & Incident Response
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(incidents_router, prefix="/incidents", tags=["incidents"])
api_router.include_router(evidence_router, prefix="/evidence", tags=["evidence"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

# Analytics & Auditing
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(audit_router, prefix="/audit-logs", tags=["audit"])

