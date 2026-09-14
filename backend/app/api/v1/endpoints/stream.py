"""Server-Sent Events (SSE) live streaming endpoint."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.analysis import AnalysisStatus
from app.models.user import User
from app.repositories.analysis import AnalysisRepository

router = APIRouter()
settings = get_settings()


async def event_generator(
    analysis_id: uuid.UUID,
    organization_id: uuid.UUID,
    session: AsyncSession,
) -> AsyncGenerator[str, None]:
    repo = AnalysisRepository(session)
    
    # 1. Send initial state immediately
    current = await repo.get_by_id_and_org(analysis_id, organization_id)
    if not current:
        yield f"data: {json.dumps({'error': 'Not found'})}\n\n"
        return

    yield f"data: {json.dumps({'status': current.status.value, 'id': str(current.id)})}\n\n"
    if current.status in (AnalysisStatus.completed, AnalysisStatus.failed):
        return

    # 2. Try Redis PubSub subscription
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        channel = f"analyses:{analysis_id}"
        await pubsub.subscribe(channel)

        timeout_seconds = 120
        elapsed = 0

        while elapsed < timeout_seconds:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg["type"] == "message":
                data_str = msg["data"].decode("utf-8") if isinstance(msg["data"], bytes) else str(msg["data"])
                yield f"data: {data_str}\n\n"
                try:
                    parsed = json.loads(data_str)
                    if parsed.get("status") in ("completed", "failed"):
                        break
                except Exception:
                    pass
            
            # Send keepalive heartbeat comment every 15 seconds
            if elapsed % 15 == 0 and elapsed > 0:
                yield ": keepalive\n\n"

            await asyncio.sleep(0.5)
            elapsed += 1

        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await r.aclose()

    except Exception:
        # Fallback polling loop if Redis is not running
        for _ in range(30):
            await asyncio.sleep(1.5)
            chk = await repo.get_by_id_and_org(analysis_id, organization_id)
            if chk:
                yield f"data: {json.dumps({'status': chk.status.value, 'id': str(chk.id)})}\n\n"
                if chk.status in (AnalysisStatus.completed, AnalysisStatus.failed):
                    break


@router.get(
    "/analyses/{analysis_id}/stream",
    summary="Subscribe to live SSE updates for an analysis job",
)
async def stream_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    repo = AnalysisRepository(session)
    analysis = await repo.get_by_id_and_org(analysis_id, current_user.organization_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    return StreamingResponse(
        event_generator(analysis_id, current_user.organization_id, session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
