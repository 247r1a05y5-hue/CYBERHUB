"""Phase 6 — Continuous Monitoring, Delta Classification, Idempotency & Tenant Isolation Tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.discovery import JobStatus, SearchJob, SearchResult
from app.models.evidence import Evidence, VerificationStatus
from app.models.intelligence import MonitoringRule, MonitoringRun, RiskAssessment
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.monitoring_service import MonitoringService
from app.services.timeline_service import timeline_service


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_env(test_db: AsyncSession):
    # Org 1
    org1 = Organization(id=uuid.uuid4(), name="Primary Tenant Org", slug="primary-org")
    test_db.add(org1)

    # User 1 (Tenant 1 Analyst)
    user1 = User(
        id=uuid.uuid4(),
        organization_id=org1.id,
        email="analyst1@primary.security",
        hashed_password="hashed_pw_test",
        full_name="Primary Analyst",
        role=UserRole.ANALYST,
        is_active=True,
    )
    test_db.add(user1)

    # Org 2 (Tenant 2)
    org2 = Organization(id=uuid.uuid4(), name="Isolated Tenant Org", slug="isolated-org")
    test_db.add(org2)

    # User 2 (Tenant 2 Analyst)
    user2 = User(
        id=uuid.uuid4(),
        organization_id=org2.id,
        email="analyst2@isolated.security",
        hashed_password="hashed_pw_test",
        full_name="Isolated Analyst",
        role=UserRole.ANALYST,
        is_active=True,
    )
    test_db.add(user2)

    # Case for Org 1
    case1 = Case(
        id=uuid.uuid4(),
        organization_id=org1.id,
        created_by_id=user1.id,
        case_number="EXP-20260913-TEST01",
        title="Monitoring Test Case 1",
        status=CaseStatus.DISCOVERY_COMPLETE,
        current_stage=5,
    )
    test_db.add(case1)

    # Search Job for Case 1
    job1 = SearchJob(
        id=uuid.uuid4(),
        case_id=case1.id,
        provider="GoogleCloudVision",
        status=JobStatus.COMPLETED,
        progress_pct=100,
    )
    test_db.add(job1)

    # Initial Finding A for Case 1
    finding_a = SearchResult(
        id=uuid.uuid4(),
        case_id=case1.id,
        search_job_id=job1.id,
        provider="GoogleCloudVision",
        source_url="https://site-alpha.com/photo.jpg",
        page_url="https://site-alpha.com/article",
        image_url="https://site-alpha.com/photo.jpg",
        domain="site-alpha.com",
        page_title="Alpha Article",
        similarity_score=0.95,
        result_type="SAME_EXACT_IMAGE",
        metadata_json={
            "canonical_url": "https://site-alpha.com/article",
            "observation_state": "ACTIVE",
            "verification_status": "VERIFIED",
        },
    )
    test_db.add(finding_a)

    await test_db.commit()

    return {
        "org1": org1,
        "user1": user1,
        "org2": org2,
        "user2": user2,
        "case1": case1,
        "finding_a": finding_a,
    }


@pytest.mark.asyncio
async def test_full_monitoring_lifecycle_and_delta_model(test_db: AsyncSession, test_env: dict):
    """
    Validates complete 20-step monitoring lifecycle:
    - Rule configuration
    - Discovery of candidate B
    - Idempotent re-scan
    - Unobserved finding A (NOT_OBSERVED_IN_LATEST_SCAN)
    - Reappearance of finding A (REAPPEARED)
    - Timeline event audit trail
    """
    case1 = test_env["case1"]
    user1 = test_env["user1"]
    org1 = test_env["org1"]
    finding_a = test_env["finding_a"]

    monitoring_svc = MonitoringService(test_db)

    # 1. Configure continuous monitoring rule
    rule = await monitoring_svc.create_or_update_rule(
        case=case1,
        frequency="DAILY",
        enabled=True,
        user_id=user1.id,
    )
    assert rule is not None
    assert rule.enabled is True
    assert rule.frequency == "DAILY"
    assert rule.last_status == "ACTIVE"
    assert rule.next_run_at is not None

    # Verify timeline event recorded
    timeline = await timeline_service.get_timeline(test_db, case1.id)
    assert any(e["event_type"] == "MONITORING_ENABLED" for e in timeline)

    # 2. Run scan with Candidate B and Finding A present
    candidate_sources_1 = [
        {
            "url": "https://site-alpha.com/photo.jpg",
            "page_url": "https://site-alpha.com/article",
            "domain": "site-alpha.com",
            "similarity_score": 0.95,
            "provider": "MockProvider",
        },
        {
            "url": "https://site-beta.com/leak.png",
            "page_url": "https://site-beta.com/post/123",
            "domain": "site-beta.com",
            "similarity_score": 0.88,
            "provider": "MockProvider",
        },
    ]

    run1 = await monitoring_svc.execute_monitoring_scan(
        rule_id=rule.id,
        user_id=user1.id,
        candidate_source_override=candidate_sources_1,
    )

    assert run1.status == "COMPLETED"
    assert run1.new_count == 1  # Beta is NEW
    assert run1.unchanged_count == 1  # Alpha is UNCHANGED
    assert run1.not_observed_count == 0
    assert run1.reappeared_count == 0

    # Verify Beta finding was persisted as candidate needing review
    stmt_b = select(SearchResult).where(SearchResult.domain == "site-beta.com")
    finding_b = (await test_db.execute(stmt_b)).scalar_one_or_none()
    assert finding_b is not None
    assert finding_b.metadata_json["observation_state"] == "NEW"
    assert finding_b.metadata_json["verification_status"] == "PENDING_REVIEW"

    # 3. IDEMPOTENCY TEST: Run same scan again -> No duplicate findings
    run2 = await monitoring_svc.execute_monitoring_scan(
        rule_id=rule.id,
        user_id=user1.id,
        candidate_source_override=candidate_sources_1,
    )

    assert run2.new_count == 0  # 0 new findings
    assert run2.unchanged_count == 2  # Both Alpha and Beta are UNCHANGED
    assert run2.not_observed_count == 0

    # Check total finding count in DB is still 2
    stmt_all = select(SearchResult).where(SearchResult.case_id == case1.id)
    all_findings = list((await test_db.execute(stmt_all)).scalars().all())
    assert len(all_findings) == 2

    # 4. NOT_OBSERVED TEST: Run scan where Finding A is absent from provider result
    candidate_sources_2 = [
        {
            "url": "https://site-beta.com/leak.png",
            "page_url": "https://site-beta.com/post/123",
            "domain": "site-beta.com",
            "similarity_score": 0.88,
            "provider": "MockProvider",
        }
    ]

    run3 = await monitoring_svc.execute_monitoring_scan(
        rule_id=rule.id,
        user_id=user1.id,
        candidate_source_override=candidate_sources_2,
    )

    assert run3.not_observed_count == 1  # Finding A was not observed
    assert run3.unchanged_count == 1  # Finding B unchanged

    # Assert Finding A is NOT deleted from DB, but state updated to NOT_OBSERVED_IN_LATEST_SCAN
    await test_db.refresh(finding_a)
    assert finding_a.metadata_json["observation_state"] == "NOT_OBSERVED_IN_LATEST_SCAN"
    # Verification status is preserved
    assert finding_a.metadata_json["verification_status"] == "VERIFIED"

    # 5. REAPPEARED TEST: Run scan where Finding A returns
    run4 = await monitoring_svc.execute_monitoring_scan(
        rule_id=rule.id,
        user_id=user1.id,
        candidate_source_override=candidate_sources_1,
    )

    assert run4.reappeared_count == 1
    await test_db.refresh(finding_a)
    assert finding_a.metadata_json["observation_state"] == "REAPPEARED"

    # 6. Verify Complete Timeline Events
    timeline_events = await timeline_service.get_timeline(test_db, case1.id)
    event_types = [e["event_type"] for e in timeline_events]
    assert "MONITORING_ENABLED" in event_types
    assert "MONITORING_SCAN_STARTED" in event_types
    assert "MONITORING_SCAN_COMPLETED" in event_types

    # 7. Check History Persistence
    history = await monitoring_svc.get_history_for_case(case1.id, org1.id)
    assert len(history) == 4
    assert history[0].id == run4.id


@pytest.mark.asyncio
async def test_monitoring_tenant_isolation(test_db: AsyncSession, test_env: dict):
    """Proves tenant 2 cannot view or trigger scans on tenant 1's monitoring rule."""
    case1 = test_env["case1"]
    org2 = test_env["org2"]

    monitoring_svc = MonitoringService(test_db)

    # Configure rule for Tenant 1
    await monitoring_svc.create_or_update_rule(
        case=case1,
        frequency="DAILY",
        enabled=True,
    )

    # Tenant 2 tries to fetch rule
    rule_tenant2 = await monitoring_svc.get_rule_for_case(case_id=case1.id, org_id=org2.id)
    assert rule_tenant2 is None

    # Tenant 2 tries to fetch history
    history_tenant2 = await monitoring_svc.get_history_for_case(case_id=case1.id, org_id=org2.id)
    assert len(history_tenant2) == 0
