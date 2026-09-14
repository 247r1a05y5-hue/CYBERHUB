"""Response Center & Takedown Package Service.

Generates formal, actionable takedown and disclosure response packages directly
from verified investigation findings and sealed evidence.

Security Constraints:
- NEVER performs automated outbound communications to external hosts or owners.
- Packages are assembled strictly for manual export and review by authorized personnel.
- All included URLs and domain references are verified and bounded by the investigation scope.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.biometrics import ReferenceImage
from app.models.case import Case
from app.models.evidence import Evidence, VerificationStatus
from app.models.intelligence import ResponsePackage
from app.models.user import User
from app.services.exposure_scan_orchestrator import ScanProgressEvent, exposure_scan_orchestrator
from app.services.secure_storage_service import secure_storage_service
from app.services.timeline_service import timeline_service

logger = logging.getLogger(__name__)


class ResponsePackageService:
    """Creates and manages standardized takedown and response packages."""

    @classmethod
    async def create_package(
        cls,
        db: AsyncSession,
        case: Case,
        target_domain: str,
        target_entity: str | None = None,
        finding_ids: list[uuid.UUID] | None = None,
        package_format: str = "MARKDOWN",
        user: User | None = None,
    ) -> ResponsePackage:
        """Generate response and takedown documentation package for verified findings on target domain."""
        user_id = user.id if user else None

        # Fetch Reference Image
        ref_stmt = select(ReferenceImage).where(ReferenceImage.case_id == case.id)
        ref_res = await db.execute(ref_stmt)
        ref_images = ref_res.scalars().all()
        ref = next((r for r in ref_images if r.is_primary), None) or (ref_images[0] if ref_images else None)
        ref_sha256 = ref.sha256_hash if ref else "UNKNOWN"

        # Fetch Verified Evidence items for target domain
        ev_stmt = select(Evidence).where(
            Evidence.case_id == case.id,
            Evidence.verification_status == VerificationStatus.VERIFIED,
        )
        if target_domain:
            ev_stmt = ev_stmt.where(Evidence.domain == target_domain)
        ev_res = await db.execute(ev_stmt)
        evidence_items = ev_res.scalars().all()

        manifest = [
            {
                "evidence_number": ev.evidence_number,
                "custody_sequence": ev.custody_sequence,
                "domain": ev.domain,
                "page_url": ev.page_url,
                "image_url": ev.image_url,
                "sha256_hash": ev.sha256_hash,
                "verified_at": ev.verified_at.isoformat() if ev.verified_at else None,
            }
            for ev in evidence_items
        ]

        entity_name = target_entity or f"Abuse & Compliance Department ({target_domain})"
        package_number = f"RSP-{uuid.uuid4().hex[:8].upper()}"

        incident_summary = (
            f"Unauthorized exposure of visual asset identified on {target_domain}. "
            f"A total of {len(evidence_items)} verified public occurrences have been cryptographically preserved."
        )

        takedown_letter = cls._generate_takedown_markdown(
            package_number=package_number,
            case_number=case.case_number,
            target_entity=entity_name,
            target_domain=target_domain,
            ref_sha256=ref_sha256,
            manifest=manifest,
        )

        contact_channels = {
            "domain": target_domain,
            "recommended_contacts": [
                f"abuse@{target_domain}",
                f"legal@{target_domain}",
                f"dmca@{target_domain}",
            ],
            "registrar_abuse_url": f"https://www.whois.com/whois/{target_domain}",
        }

        # Compute deterministic package hash
        content_for_hash = json.dumps(
            {
                "package_number": package_number,
                "case_id": str(case.id),
                "domain": target_domain,
                "manifest": manifest,
                "letter": takedown_letter,
            },
            sort_keys=True,
        ).encode("utf-8")
        package_sha256 = hashlib.sha256(content_for_hash).hexdigest()

        # Save ResponsePackage record
        pkg = ResponsePackage(
            case_id=case.id,
            package_number=package_number,
            target_domain=target_domain,
            target_entity=entity_name,
            incident_summary=incident_summary,
            evidence_manifest_json=manifest,
            takedown_letter_markdown=takedown_letter,
            contact_channels_json=contact_channels,
            package_format=package_format.upper(),
            sha256_hash=package_sha256,
            status="READY",
            created_by_id=user_id,
        )
        db.add(pkg)
        await db.flush()

        # Append Timeline Event
        await timeline_service.record_event(
            db=db,
            case_id=case.id,
            event_type="RESPONSE_PACKAGE_GENERATED",
            title=f"Response Package Generated for {target_domain}",
            description=f"Generated formal takedown notice {package_number} referencing {len(manifest)} verified artifact(s).",
            actor_id=user_id,
            metadata={"package_number": package_number, "domain": target_domain, "sha256": package_sha256},
        )

        # Broadcast SSE Event
        await exposure_scan_orchestrator.broadcast_event(
            ScanProgressEvent(
                event_type="response.package.generated",
                investigation_id=str(case.id),
                job_id=str(pkg.id),
                step="RESPONSE_PACKAGE_READY",
                progress_pct=100,
                message=f"Takedown package {package_number} generated for {target_domain}.",
                timestamp=datetime.now(timezone.utc).isoformat(),
                payload={
                    "package_id": str(pkg.id),
                    "package_number": package_number,
                    "target_domain": target_domain,
                    "sha256_hash": package_sha256,
                    "evidence_count": len(manifest),
                },
            )
        )

        return pkg

    @classmethod
    def _generate_takedown_markdown(
        cls,
        package_number: str,
        case_number: str,
        target_entity: str,
        target_domain: str,
        ref_sha256: str,
        manifest: list[dict[str, Any]],
    ) -> str:
        """Format standardized markdown formal takedown letter."""
        lines = [
            f"# FORMAL NOTICE OF UNAUTHORIZED ASSET EXPOSURE & TAKEDOWN REQUEST",
            f"**Notice Reference:** `{package_number}`  ",
            f"**Investigation Dossier:** `{case_number}`  ",
            f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            "",
            f"**TO:**  ",
            f"Designated Agent / Abuse Department  ",
            f"**Entity:** {target_entity}  ",
            f"**Domain:** `{target_domain}`  ",
            "",
            "---",
            "",
            "### 1. Statement of Authority & Scope",
            "This communication serves as a formal notification regarding the unauthorized publication, distribution, ",
            f"or caching of protected visual assets hosted on network infrastructure under your administrative control (`{target_domain}`).",
            "",
            "### 2. Identification of Protected Subject Asset",
            f"- **Cryptographic SHA-256 Fingerprint:** `{ref_sha256}`",
            "- **Methodology:** Multi-tier invariant visual matching verifying exact/transformed instance propagation.",
            "",
            "### 3. Discovered Infringing URLs & Cryptographic Evidence",
            "The following endpoints on your domain have been confirmed and preserved with tamper-evident SHA-256 signatures:",
            "",
        ]

        if not manifest:
            lines.append("*No individual URLs specified in this notice envelope.*")
        else:
            for idx, item in enumerate(manifest, 1):
                lines.append(f"**Item {idx}:**")
                lines.append(f"- **Page URL:** {item.get('page_url')}")
                lines.append(f"- **Image Resource:** {item.get('image_url')}")
                lines.append(f"- **Evidence Record:** `{item.get('evidence_number')}` (SHA-256: `{item.get('sha256_hash')}`)")
                lines.append("")

        lines.extend([
            "### 4. Requested Action",
            "We hereby formally request that you immediately:",
            f"1. Expeditiously disable access to or remove the visual asset(s) at the specified URL(s) on `{target_domain}`.",
            "2. Invalidate any associated edge CDN or cache entries mirroring the content.",
            "3. Confirm in writing to the sender once removal has been successfully executed.",
            "",
            "### 5. Good Faith Declaration",
            "This notification is generated pursuant to a verified cyber investigation workflow. ",
            "All captured artifacts are cryptographically hashed and cataloged in an append-only audit chain.",
            "",
            "---",
            "*Generated via CyberHub Security Platform — Confidential Investigation Material*",
        ])

        return "\n".join(lines)


response_package_service = ResponsePackageService()
