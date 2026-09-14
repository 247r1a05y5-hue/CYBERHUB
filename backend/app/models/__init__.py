"""Model registry — import all models so Alembic can discover them."""
from app.db.base import Base
from app.models.alert import Alert, AlertStatus
from app.models.analysis import Analysis, AnalysisStatus, AnalysisType
from app.models.analysis_input import AnalysisInput, InputType
from app.models.analysis_result import AnalysisResult, Severity, Verdict
from app.models.attestation import InvestigationAttestation
from app.models.audit_log import AuditAction, AuditLog
from app.models.biometrics import FaceEmbedding, FaceRecord, FaceValidationStatus, ReferenceImage
from app.models.case import Case, CaseStage, CaseStatus
from app.models.dataset import Dataset, DatasetIdentity, DatasetStatus, DatasetVersion
from app.models.discovery import (
    ConfidenceCategory,
    CorrelationCluster,
    JobStatus,
    Match,
    SearchJob,
    SearchResult,
)
from app.models.evidence import Evidence, EvidenceEvent, EvidenceType, VerificationStatus
from app.models.incident import INCIDENT_TRANSITIONS, STATUSES_REQUIRING_NOTE, Incident, IncidentStatus
from app.models.incident_alert import IncidentAlert
from app.models.indicator import Indicator, IndicatorType
from app.models.intelligence import (
    Complaint,
    ComplaintStatus,
    MonitoringRule,
    MonitoringRun,
    Report,
    ReportFormat,
    ReportStatus,
    ResponsePackage,
    RiskAssessment,
    RiskLevel,
    TimelineEvent,
)
from app.models.note import Note
from app.models.notification import Notification, NotificationType
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole

__all__ = [
    "Alert",
    "AlertStatus",
    "Analysis",
    "AnalysisInput",
    "AnalysisResult",
    "AnalysisStatus",
    "AnalysisType",
    "AuditAction",
    "AuditLog",
    "Base",
    "Case",
    "CaseStage",
    "CaseStatus",
    "Complaint",
    "ComplaintStatus",
    "ConfidenceCategory",
    "CorrelationCluster",
    "Dataset",
    "DatasetIdentity",
    "DatasetStatus",
    "DatasetVersion",
    "Evidence",
    "EvidenceEvent",
    "EvidenceType",
    "FaceEmbedding",
    "FaceRecord",
    "FaceValidationStatus",
    "INCIDENT_TRANSITIONS",
    "Incident",
    "IncidentAlert",
    "IncidentStatus",
    "Indicator",
    "IndicatorType",
    "InputType",
    "InvestigationAttestation",
    "JobStatus",
    "Match",
    "MonitoringRule",
    "MonitoringRun",

    "Note",
    "Notification",
    "NotificationType",
    "Organization",
    "ReferenceImage",
    "RefreshToken",
    "Report",
    "ReportFormat",
    "ReportStatus",
    "ResponsePackage",
    "RiskAssessment",
    "RiskLevel",
    "STATUSES_REQUIRING_NOTE",
    "SearchJob",
    "SearchResult",
    "Severity",
    "TimelineEvent",
    "User",
    "UserRole",
    "Verdict",
    "VerificationStatus",
]
