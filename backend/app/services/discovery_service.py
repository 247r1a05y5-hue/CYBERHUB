"""Exposure Discovery Service — SearchProvider abstraction and async scan engine."""
from __future__ import annotations

import abc
import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction
from app.models.case import Case, CaseStatus
from app.models.discovery import JobStatus, SearchJob, SearchResult
from app.services.audit_service import AuditService


@dataclass
class NormalizedFinding:
    source_url: str
    page_url: str
    image_url: str
    domain: str
    page_title: str
    similarity_score: float
    result_type: str = "EXACT_OR_SIMILAR"
    metadata_json: dict[str, Any] | None = None


class SearchProvider(abc.ABC):
    @abc.abstractmethod
    async def search_image(self, image_url: str, reference_hash: str) -> list[NormalizedFinding]:
        """Search public web for appearances of reference image."""


class MockSearchProvider(SearchProvider):
    """Realistic mock search provider producing multi-domain exposure findings for testing & demo."""

    async def search_image(self, image_url: str, reference_hash: str) -> list[NormalizedFinding]:
        return [
            NormalizedFinding(
                source_url="https://images.credential-leak-db.net/profiles/vance_arch.png",
                page_url="https://breach-forums-archive.io/threads/executive-roster-dump-2026.8942",
                image_url="https://images.credential-leak-db.net/profiles/vance_arch.png",
                domain="breach-forums-archive.io",
                page_title="Executive Roster & Auth Keys Collection 2026",
                similarity_score=0.98,
                metadata_json={"threat_category": "UNAUTHORIZED_LEAK", "propagation": "CLUSTER_A"},
            ),
            NormalizedFinding(
                source_url="https://cdn.darkweb-intel.xyz/avatars/sec_lead_08.png",
                page_url="https://darkweb-intel.xyz/actors/profile/target_992",
                image_url="https://cdn.darkweb-intel.xyz/avatars/sec_lead_08.png",
                domain="darkweb-intel.xyz",
                page_title="Impersonation Profile / Spear-Phish Ingress Asset",
                similarity_score=0.95,
                metadata_json={"threat_category": "IMPERSONATION", "propagation": "CLUSTER_A"},
            ),
            NormalizedFinding(
                source_url="https://media.paste-repo.org/dumps/auth_tokens_img.jpg",
                page_url="https://paste-repo.org/view/raw/sec_dump_9918",
                image_url="https://media.paste-repo.org/dumps/auth_tokens_img.jpg",
                domain="paste-repo.org",
                page_title="Anonymous Paste — Infrastructure Auth Roster",
                similarity_score=0.92,
                metadata_json={"threat_category": "PUBLIC_PASTE", "propagation": "CLUSTER_B"},
            ),
            NormalizedFinding(
                source_url="https://static.unclassified-forum.cc/media/p/8841.jpg",
                page_url="https://unclassified-forum.cc/intel/threat-discussion-2026",
                image_url="https://static.unclassified-forum.cc/media/p/8841.jpg",
                domain="unclassified-forum.cc",
                page_title="Threat Intel Discussion & Target Assets",
                similarity_score=0.89,
                metadata_json={"threat_category": "FORUM_DISCUSSION", "propagation": "CLUSTER_B"},
            ),
            NormalizedFinding(
                source_url="https://asset-store.public-cloud.com/profiles/avatar.png",
                page_url="https://public-directory.corp-lookup.org/people/alex-vance",
                image_url="https://asset-store.public-cloud.com/profiles/avatar.png",
                domain="corp-lookup.org",
                page_title="Corporate Directory Index",
                similarity_score=0.99,
                metadata_json={"threat_category": "LEGITIMATE_DIRECTORY", "propagation": "CLUSTER_C"},
            ),
        ]


class GoogleCloudVisionWebDetectionProvider(SearchProvider):
    """Adapter scaffolding for Google Cloud Vision API Web Detection."""

    async def search_image(self, image_url: str, reference_hash: str) -> list[NormalizedFinding]:
        # Fallback to mock in demo environment without live Google Cloud credentials
        mock = MockSearchProvider()
        return await mock.search_image(image_url, reference_hash)


class DiscoveryService:
    """Service to execute discovery scan jobs, stream SSE events, and normalize findings."""

    def __init__(self, session: AsyncSession, provider: SearchProvider | None = None):
        self.session = session
        self.provider = provider or MockSearchProvider()
        self.audit_service = AuditService(session)

    async def create_scan_job(
        self,
        case: Case,
        provider_name: str = "GoogleCloudVisionWebDetection",
        user_id: uuid.UUID | None = None,
    ) -> SearchJob:
        """Create and queue an exposure discovery job."""
        case.status = CaseStatus.DISCOVERY_RUNNING
        case.current_stage = 3

        job = SearchJob(
            case_id=case.id,
            provider=provider_name,
            status=JobStatus.PENDING,
            progress_pct=0,
            current_step="Initializing Discovery Scan",
        )
        self.session.add(job)
        await self.session.flush()

        await self.audit_service.log(
            action=AuditAction.discovery_started,
            user_id=user_id,
            organization_id=case.organization_id,
            resource_type="case",
            resource_id=str(case.id),
            details={"job_id": str(job.id), "provider": provider_name},
        )
        return job

    async def execute_scan(self, job_id: uuid.UUID) -> list[SearchResult]:
        """Execute discovery job, query provider, normalize results, and save to DB."""
        stmt = select(SearchJob).where(SearchJob.id == job_id)
        job = (await self.session.execute(stmt)).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = JobStatus.RUNNING
        job.progress_pct = 25
        job.current_step = "Searching external web providers..."
        await self.session.flush()

        # Query provider
        findings = await self.provider.search_image(
            image_url="https://cyberhub.local/reference.jpg",
            reference_hash="mock-hash",
        )

        job.progress_pct = 75
        job.current_step = "Normalizing and deduplicating results..."
        await self.session.flush()

        # Save SearchResults
        results = []
        for f in findings:
            sr = SearchResult(
                case_id=job.case_id,
                search_job_id=job.id,
                provider=job.provider,
                source_url=f.source_url,
                page_url=f.page_url,
                image_url=f.image_url,
                domain=f.domain,
                page_title=f.page_title,
                similarity_score=f.similarity_score,
                result_type=f.result_type,
                metadata_json=f.metadata_json or {},
            )
            self.session.add(sr)
            results.append(sr)

        # Complete job & update case status
        job.status = JobStatus.COMPLETED
        job.progress_pct = 100
        job.total_found = len(results)
        job.current_step = "Discovery complete"
        job.completed_at = datetime.now(timezone.utc)

        stmt_case = select(Case).where(Case.id == job.case_id)
        case_obj = (await self.session.execute(stmt_case)).scalar_one_or_none()
        if case_obj:
            case_obj.status = CaseStatus.DISCOVERY_COMPLETE
            case_obj.current_stage = 4

        await self.session.flush()
        return results
