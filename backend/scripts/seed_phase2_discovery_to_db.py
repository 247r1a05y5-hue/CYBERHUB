"""Seed real Phase 2 SearchAPI / SerpApi Discovery results into PostgreSQL database.

Creates Organization -> User -> Case -> SearchJob -> SearchResult records
using live SearchAPI / SerpApi results so that Phase 3 Investigation Engine
has authentic Phase 2 discovery candidates to investigate.
"""
from __future__ import annotations

import asyncio
import io
import logging
import sys
import uuid
from datetime import datetime, timezone
from PIL import Image, ImageDraw
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.case import Case, CaseStatus
from app.models.discovery import SearchJob, SearchResult, JobStatus
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.provider_orchestration_service import (
    ProviderOptions,
    SearchAPIGoogleLensProvider,
    SerpApiGoogleLensProvider,
    deduplicate_discovery_results,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_phase2_discovery")


def create_probe_image() -> bytes:
    img = Image.new("RGB", (300, 300), color=(18, 30, 49))
    d = ImageDraw.Draw(img)
    d.rectangle([(20, 20), (280, 280)], outline=(0, 220, 255), width=3)
    d.ellipse([(70, 70), (230, 230)], fill=(220, 40, 40), outline=(255, 255, 255), width=2)
    d.text((45, 135), "CYBERHUB PROBE 2026", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


async def seed_discovery_records():
    print("=" * 75)
    print("SEEDING REAL PHASE 2 DISCOVERY RESULTS INTO DATABASE")
    print("=" * 75)

    public_probe_url = "https://images.unsplash.com/photo-1544005313-94ddf0286df2"
    img_bytes = create_probe_image()

    searchapi_key = getattr(settings, "SEARCHAPI_API_KEY", None)
    serpapi_key = getattr(settings, "SERPAPI_API_KEY", None)

    all_raw_results = []
    
    if searchapi_key:
        print("Querying live SearchAPI Google Lens endpoint...")
        try:
            sp = SearchAPIGoogleLensProvider(api_key=searchapi_key)
            res = await sp.discover(img_bytes, public_probe_url, ProviderOptions(max_results=20))
            all_raw_results.extend(res)
            print(f"  SearchAPI returned {len(res)} results")
        except Exception as e:
            print(f"  SearchAPI warning: {e}")

    if serpapi_key:
        print("Querying live SerpApi Google Lens endpoint...")
        try:
            sp2 = SerpApiGoogleLensProvider(api_key=serpapi_key)
            res2 = await sp2.discover(img_bytes, public_probe_url, ProviderOptions(max_results=20))
            all_raw_results.extend(res2)
            print(f"  SerpApi returned {len(res2)} results")
        except Exception as e:
            print(f"  SerpApi warning: {e}")

    deduped = deduplicate_discovery_results(all_raw_results)
    print(f"\nTotal deduplicated discovery results to insert: {len(deduped)}")

    if not deduped:
        print("ERROR: No discovery results obtained from live providers.")
        sys.exit(1)

    async with async_session_factory() as session:
        # 1. Get or create Org
        res_org = await session.execute(select(Organization).limit(1))
        org = res_org.scalar_one_or_none()
        if not org:
            org = Organization(
                id=uuid.uuid4(),
                name="CYBERHUB Default Security Ops",
                slug="cyberhub-ops",
                is_active=True,
            )
            session.add(org)
            await session.flush()
        print(f"Using Organization: {org.name} ({org.id})")

        # 2. Get or create User
        res_user = await session.execute(select(User).where(User.organization_id == org.id).limit(1))
        user = res_user.scalar_one_or_none()
        if not user:
            user = User(
                id=uuid.uuid4(),
                organization_id=org.id,
                email="admin@cyberhub.dev",
                hashed_password=hash_password("Admin1234!"),
                full_name="System Admin",
                role=UserRole.admin,
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.flush()
        print(f"Using User: {user.email} ({user.id})")

        # 3. Get or create Case
        res_case = await session.execute(select(Case).where(Case.organization_id == org.id).limit(1))
        case = res_case.scalar_one_or_none()
        if not case:
            case = Case(
                id=uuid.uuid4(),
                organization_id=org.id,
                created_by_id=user.id,
                case_number=f"CASE-{uuid.uuid4().hex[:8].upper()}",
                title="Phase 2/3 Web Discovery Exposure Case",
                description="Live exposure discovery test case for web investigation pipeline",
                status=CaseStatus.DRAFT,
            )
            session.add(case)
            await session.flush()
        print(f"Using Case: {case.title} ({case.id})")

        # 4. Create SearchJob
        search_job = SearchJob(
            id=uuid.uuid4(),
            case_id=case.id,
            provider="SearchAPI+SerpApi",
            status=JobStatus.COMPLETED,
            total_found=len(deduped),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(search_job)
        await session.flush()

        def to_str_url(v: Any, fallback: str = "") -> str:
            if isinstance(v, dict):
                return str(v.get("link") or v.get("url") or v.get("src") or fallback)
            return str(v) if v else fallback

        # 5. Insert SearchResult records
        inserted = 0
        for item in deduped:
            res_url = to_str_url(item.result_url)
            pg_url = to_str_url(item.page_url, fallback=res_url)
            src_url = to_str_url(item.source_url, fallback=res_url)
            img_url = to_str_url(item.image_url, fallback=to_str_url(item.thumbnail_url, fallback=res_url))

            sr = SearchResult(
                id=uuid.uuid4(),
                case_id=case.id,
                search_job_id=search_job.id,
                provider=item.provider,
                source_url=src_url,
                page_url=pg_url,
                image_url=img_url,
                domain=item.domain or "unknown.com",
                page_title=item.page_title or item.title,
                similarity_score=getattr(item, "provider_score", 0.9) or 0.9,
                result_type=item.result_type or "VISUAL_MATCH",
                metadata_json={
                    "source_provider": item.provider,
                    "provider_result_id": item.provider_result_id,
                    "metadata": item.provider_metadata,
                },
            )
            session.add(sr)
            inserted += 1

        await session.commit()
        print(f"Successfully inserted {inserted} real SearchResult records into database.")
        print("=" * 75)


if __name__ == "__main__":
    asyncio.run(seed_discovery_records())
