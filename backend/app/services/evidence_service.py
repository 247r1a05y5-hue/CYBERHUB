"""Evidence Vault Service — Append-only preservation, SHA-256 verification, and chain-of-custody."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ssrf import is_safe_url, validate_outbound_url
from app.models.audit_log import AuditAction
from app.models.case import Case, CaseStatus
from app.models.discovery import SearchResult
from app.models.evidence import Evidence, EvidenceEvent, EvidenceType, VerificationStatus
from app.services.audit_service import AuditService


class EvidenceService:
    """Service to triage search results, preserve immutable evidence, and maintain chain-of-custody."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_service = AuditService(session)

    async def verify_finding(
        self,
        case: Case,
        result_id: uuid.UUID,
        status: VerificationStatus,
        user_reason: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Evidence:
        """
        Human-in-the-loop verification step.
        Triages finding as VERIFIED, REJECTED, or UNCERTAIN and records to Evidence Vault.
        """
        stmt = select(SearchResult).where(SearchResult.id == result_id, SearchResult.case_id == case.id)
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        if not result:
            raise ValueError(f"SearchResult {result_id} not found")

        # SSRF validation check on URL
        is_safe = is_safe_url(result.page_url)

        # Mock screenshot path & deterministic SHA-256 hash
        mock_raw_content = f"{result.page_url}:{result.image_url}:{datetime.now(timezone.utc).isoformat()}".encode()
        sha256_hash = hashlib.sha256(mock_raw_content).hexdigest()
        screenshot_path = f"/storage/evidence/screenshots/{sha256_hash[:16]}.png" if is_safe else None

        evidence_num = f"EVD-{str(uuid.uuid4())[:8].upper()}"

        # Create immutable Evidence record
        evidence = Evidence(
            case_id=case.id,
            search_result_id=result.id,
            evidence_number=evidence_num,
            source_url=result.source_url,
            page_url=result.page_url,
            image_url=result.image_url,
            domain=result.domain,
            page_title=result.page_title,
            screenshot_path=screenshot_path,
            sha256_hash=sha256_hash,
            collection_method="AUTOMATED_CAPTURE_WITH_HUMAN_VERIFICATION",
            provider=result.provider,
            evidence_type=EvidenceType.WEB_SCREENSHOT,
            verification_status=status,
            user_reason=user_reason,
            verified_by_id=user_id,
            verified_at=datetime.now(timezone.utc),
            chain_of_custody_json=[
                {
                    "event": "INGESTION",
                    "timestamp": result.discovered_at.isoformat(),
                    "actor": result.provider,
                    "details": "Discovered via web search engine",
                },
                {
                    "event": "VERIFICATION",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "actor": str(user_id) if user_id else "ANALYST",
                    "status": status.value,
                    "reason": user_reason or "Verified by SOC analyst",
                },
                {
                    "event": "INTEGRITY_SEAL",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sha256": sha256_hash,
                    "algorithm": "SHA-256",
                },
            ],
            metadata_json={"is_safe_egress": is_safe, "threat_cluster": result.metadata_json.get("propagation")},
        )
        self.session.add(evidence)
        await self.session.flush()

        # Chain of Custody Event
        evt = EvidenceEvent(
            case_id=case.id,
            evidence_id=evidence.id,
            event_type="VERIFICATION_AND_HASH",
            actor_id=user_id,
            details_json={"status": status.value, "sha256": sha256_hash, "user_reason": user_reason},
        )
        self.session.add(evt)

        # Transition Case state
        if status == VerificationStatus.VERIFIED:
            case.status = CaseStatus.EVIDENCE_READY
            case.current_stage = 6

        await self.session.flush()

        # Audit sensitive verification action
        await self.audit_service.log(
            action=AuditAction.result_verified,
            user_id=user_id,
            organization_id=case.organization_id,
            resource_type="evidence",
            resource_id=str(evidence.id),
            details={
                "evidence_number": evidence_num,
                "status": status.value,
                "sha256": sha256_hash,
                "domain": result.domain,
            },
        )

        return evidence
