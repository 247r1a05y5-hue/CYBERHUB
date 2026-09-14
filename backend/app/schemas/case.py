"""Pydantic schemas for CyberHub Case and workflow operations."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    target_subject_label: str | None = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_number: str
    title: str
    description: str | None = None
    target_subject_label: str | None = None
    status: str
    current_stage: int
    created_at: datetime
    updated_at: datetime


class CaptureUploadRequest(BaseModel):
    image_base64: str | None = None
    image_url: str | None = None


class CaptureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference_image_id: uuid.UUID
    image_url: str
    sha256_hash: str
    quality_score: float
    face_count: int
    validation_status: str
    is_valid: bool


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    dataset_identity_id: uuid.UUID
    candidate_name: str | None = None
    candidate_code: str | None = None
    photo_url: str | None = None
    similarity_score: float
    confidence_category: str
    is_confirmed: bool
    review_notes: str | None = None
    signals: dict[str, Any] = Field(default_factory=dict)


class MatchConfirmRequest(BaseModel):
    match_id: uuid.UUID
    confirmed: bool
    review_notes: str | None = None


class ScanJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    case_id: uuid.UUID
    provider: str
    status: str
    progress_pct: int
    current_step: str | None = None
    total_found: int


class SearchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    source_url: str
    page_url: str
    image_url: str
    domain: str
    page_title: str | None = None
    discovered_at: datetime
    similarity_score: float
    result_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerifyFindingRequest(BaseModel):
    result_id: uuid.UUID
    status: str  # VERIFIED, REJECTED, UNCERTAIN
    user_reason: str | None = None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evidence_number: str
    source_url: str
    page_url: str
    image_url: str
    domain: str
    page_title: str | None = None
    screenshot_path: str | None = None
    sha256_hash: str
    verification_status: str
    user_reason: str | None = None
    chain_of_custody: list[dict[str, Any]] = Field(default_factory=list)


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    overall_risk_level: str
    calculated_score: float
    explanation_text: str
    factor_breakdown: dict[str, Any] = Field(default_factory=dict)


class ReportGenerateRequest(BaseModel):
    format: str = "PDF"


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_title: str
    report_format: str
    file_path: str | None = None
    sha256_hash: str
    generated_at: datetime
    summary: dict[str, Any] = Field(default_factory=dict)


class ComplaintDraftRequest(BaseModel):
    target_entity: str


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_entity: str
    incident_summary: str
    draft_body: str
    status: str


class ComplaintReviewRequest(BaseModel):
    status: str = "REVIEWED"


class MonitoringRuleRequest(BaseModel):
    frequency: str = "DAILY"
    enabled: bool = True


class MonitoringRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    frequency: str
    enabled: bool
    previous_count: int
    current_count: int
    new_delta_count: int
    last_run_at: datetime | None = None
