"""Analysis schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field

from app.models.analysis import AnalysisStatus
from app.models.analysis_input import InputType
from app.models.analysis_result import Severity, Verdict
from app.schemas.common import ORMBase


class AnalysisSubmissionRequest(BaseModel):
    analyzer_type: str = Field(default="mock", description="Analyzer plugin name e.g. mock")
    input_type: InputType = Field(default=InputType.text, description="url, file, email, text, hash, ip, domain, json")
    payload: Optional[str] = Field(default=None, description="Direct text / payload if not file upload")
    raw_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata dictionary")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom analysis options")


class AnalysisInputResponse(ORMBase):
    id: uuid.UUID
    analysis_id: uuid.UUID
    input_type: InputType
    storage_ref: Optional[str] = None
    raw_metadata: Optional[Dict[str, Any]] = None
    sha256: Optional[str] = None


class AnalysisResultResponse(ORMBase):
    id: uuid.UUID
    analysis_id: uuid.UUID
    verdict: Verdict
    severity: Severity
    risk_score: float
    confidence: float
    summary: Optional[str] = None
    reasons: Optional[List[Any]] = None
    contributing_factors: Optional[List[Any]] = None
    recommendations: Optional[List[Any]] = None
    indicators: Optional[List[Any]] = None
    model_version: Optional[str] = None
    rule_pack_version: Optional[str] = None
    policy_version: Optional[str] = None
    raw_findings: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime


class AnalysisResponse(ORMBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_by_id: Optional[uuid.UUID] = None
    analyzer_type: str
    status: AnalysisStatus
    content_hash: Optional[str] = None
    job_id: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    tags: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    input: Optional[AnalysisInputResponse] = None
    result: Optional[AnalysisResultResponse] = None


class AnalysisSummary(ORMBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_by_id: Optional[uuid.UUID] = None
    analyzer_type: str
    status: AnalysisStatus
    content_hash: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime
    verdict: Optional[Verdict] = None
    severity: Optional[Severity] = None
    risk_score: Optional[float] = None
