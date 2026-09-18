"""RQ background jobs for CyberHub async execution."""
from __future__ import annotations

import asyncio
import uuid

from app.db.session import AsyncSessionLocal
from app.services.discovery_service import DiscoveryService
from app.services.evidence_service import EvidenceService
from app.services.monitoring_service import MonitoringService
from app.services.risk_service import RiskService


def run_async(coro):
    """Helper to run async coroutines in synchronous RQ worker threads."""
    return asyncio.run(coro)


def job_web_discovery(job_id_str: str) -> dict:
    """Async worker job to execute web discovery scan idempotently."""
    async def _run():
        async with AsyncSessionLocal() as session:
            discovery_service = DiscoveryService(session)
            job_id = uuid.UUID(job_id_str)
            results = await discovery_service.execute_scan(job_id)
            await session.commit()
            return {"job_id": job_id_str, "status": "COMPLETED", "found_count": len(results)}

    return run_async(_run())


def job_monitoring_scan(rule_id_str: str) -> dict:
    """Async worker job to execute scheduled monitoring re-scan."""
    async def _run():
        async with AsyncSessionLocal() as session:
            monitoring_service = MonitoringService(session)
            rule_id = uuid.UUID(rule_id_str)
            prev, now, delta = await monitoring_service.execute_monitoring_scan(rule_id)
            await session.commit()
            return {"rule_id": rule_id_str, "before": prev, "now": now, "new": delta}

    return run_async(_run())


def run_analysis_job(analysis_id_str: str) -> dict:
    """Async worker job to execute analysis pipeline."""
    async def _run():
        async with AsyncSessionLocal() as session:
            from app.services.analysis_orchestrator import AnalysisOrchestrator
            orchestrator = AnalysisOrchestrator(session)
            analysis_id = uuid.UUID(analysis_id_str)
            finding = await orchestrator.run_pipeline(analysis_id)
            await session.commit()
            return {"analysis_id": analysis_id_str, "status": finding.status.value if hasattr(finding, "status") else "COMPLETED"}

    return run_async(_run())
