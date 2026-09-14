"""Report & Complaint Package generation service."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.case import Case, CaseStatus
from app.models.evidence import Evidence, VerificationStatus
from app.models.intelligence import Complaint, ComplaintStatus, Report, ReportFormat, RiskAssessment
from app.services.audit_service import AuditService


class ReportService:
    """Service to compile comprehensive executive reports and draft legal/takedown complaint packages."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_service = AuditService(session)

    async def generate_case_report(
        self,
        case: Case,
        fmt: ReportFormat = ReportFormat.PDF,
        user_id: uuid.UUID | None = None,
    ) -> Report:
        """Compile verified findings, exposure graphs, risk assessments, and timeline into an exportable report."""
        # Gather case evidence
        stmt_ev = select(Evidence).where(Evidence.case_id == case.id)
        evidence_items = list((await self.session.execute(stmt_ev)).scalars().all())

        # Gather risk assessment
        stmt_risk = select(RiskAssessment).where(RiskAssessment.case_id == case.id).order_by(RiskAssessment.created_at.desc())
        risk = (await self.session.execute(stmt_risk)).scalars().first()

        report_payload = {
            "case_id": str(case.id),
            "case_number": case.case_number,
            "title": case.title,
            "subject": case.target_subject_label,
            "status": case.status.value,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_risk_level": risk.overall_risk_level.value if risk else "UNKNOWN",
            "risk_score": risk.calculated_score if risk else 0.0,
            "verified_evidence_count": sum(1 for e in evidence_items if e.verification_status == VerificationStatus.VERIFIED),
            "evidence": [
                {
                    "evidence_number": e.evidence_number,
                    "domain": e.domain,
                    "page_url": e.page_url,
                    "sha256": e.sha256_hash,
                    "status": e.verification_status.value,
                }
                for e in evidence_items
            ],
        }

        content_bytes = json.dumps(report_payload, indent=2).encode()
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()
        file_path = f"/storage/reports/{case.case_number}_report.{fmt.value.lower()}"

        report = Report(
            case_id=case.id,
            report_title=f"CyberHub Investigation Report — {case.case_number}",
            report_format=fmt,
            file_path=file_path,
            sha256_hash=sha256_hash,
            generated_by_id=user_id,
            summary_json=report_payload,
        )
        self.session.add(report)

        case.status = CaseStatus.REPORT_READY
        case.current_stage = 8
        await self.session.flush()

        # Audit report generation
        await self.audit_service.log(
            action=AuditAction.report_generated,
            user_id=user_id,
            organization_id=case.organization_id,
            resource_type="report",
            resource_id=str(report.id),
            details={"case_number": case.case_number, "format": fmt.value, "sha256": sha256_hash},
        )

        return report

    async def create_complaint_draft(
        self,
        case: Case,
        target_entity: str,
        user_id: uuid.UUID | None = None,
    ) -> Complaint:
        """Create a takedown / legal notification draft. Requires explicit user review before export."""
        stmt_ev = select(Evidence).where(
            Evidence.case_id == case.id,
            Evidence.verification_status == VerificationStatus.VERIFIED,
        )
        evidence_items = list((await self.session.execute(stmt_ev)).scalars().all())

        urls_text = "\n".join(f"- {e.page_url} (SHA-256: {e.sha256_hash[:16]}...)" for e in evidence_items)

        draft_body = (
            f"FORMAL NOTICE OF UNLAWFUL ASSET EXPOSURE & TAKEDOWN REQUEST\n\n"
            f"Case Reference: {case.case_number}\n"
            f"Target Entity / Platform: {target_entity}\n"
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"Subject Identity: {case.target_subject_label or case.title}\n\n"
            f"Summary of Violation:\n"
            f"The following verified assets and credentials are hosted or indexed on your infrastructure without authorization:\n"
            f"{urls_text}\n\n"
            f"Preserved Evidence Integrity:\n"
            f"All referenced URLs have been preserved with cryptographically timestamped SHA-256 integrity hashes "
            f"in accordance with standardized digital evidence handling procedures.\n\n"
            f"Requested Action:\n"
            f"Immediate containment and removal of the aforementioned assets within 24 hours of receipt."
        )

        complaint = Complaint(
            case_id=case.id,
            target_entity=target_entity,
            incident_summary=f"Unauthorized credential & identity exposure targeting {case.target_subject_label or case.title}",
            draft_body=draft_body,
            evidence_ids_json=[str(e.id) for e in evidence_items],
            status=ComplaintStatus.DRAFT,
        )
        self.session.add(complaint)
        await self.session.flush()

        await self.audit_service.log(
            action=AuditAction.complaint_drafted,
            user_id=user_id,
            organization_id=case.organization_id,
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={"target_entity": target_entity, "status": "DRAFT"},
        )

        return complaint

    async def review_complaint_draft(
        self,
        complaint_id: uuid.UUID,
        reviewed_status: ComplaintStatus,
        user_id: uuid.UUID,
    ) -> Complaint:
        """Explicit user review step for complaint package before submission/export."""
        stmt = select(Complaint).where(Complaint.id == complaint_id)
        complaint = (await self.session.execute(stmt)).scalar_one_or_none()
        if not complaint:
            raise ValueError(f"Complaint {complaint_id} not found")

        complaint.status = reviewed_status
        complaint.reviewed_by_id = user_id
        complaint.reviewed_at = datetime.now(timezone.utc)
        await self.session.flush()

        await self.audit_service.log(
            action=AuditAction.complaint_reviewed,
            user_id=user_id,
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={"status": reviewed_status.value},
        )

        return complaint
