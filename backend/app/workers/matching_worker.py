"""RQ Worker Task for Phase 3 Investigation Matching."""
from __future__ import annotations

import asyncio
import uuid

from app.db.session import AsyncSessionLocal
from app.services.matching_orchestrator import matching_orchestrator


def run_async(coro):
    """Helper to run async coroutines in synchronous RQ worker threads."""
    return asyncio.run(coro)


def job_process_investigation_matching(investigation_id_str: str, organization_id_str: str) -> dict:
    """Async RQ job executing full 3-tier matching pipeline."""
    async def _run():
        async with AsyncSessionLocal() as session:
            inv_id = uuid.UUID(investigation_id_str)
            org_id = uuid.UUID(organization_id_str)
            candidates = await matching_orchestrator.execute_matching(
                db=session,
                investigation_id=inv_id,
                organization_id=org_id,
            )
            return {
                "investigation_id": investigation_id_str,
                "status": "COMPLETED",
                "candidate_count": len(candidates),
            }

    return run_async(_run())
