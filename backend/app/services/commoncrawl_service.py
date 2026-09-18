"""Common Crawl Historical Index Lookup Service.

Queries Common Crawl CDX Index API to determine historical presence in open web crawls.
Preserves explicit semantics:
- Record found -> OBSERVED (crawl ID, offset, digest)
- No record found -> NOT_OBSERVED (preserves uncertainty)
- Never executes bulk WARC downloads (bounded index queries only)
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation_record import HistoricalSnapshot, HistoricalSource, SnapshotStatus

logger = logging.getLogger(__name__)

# Primary active Common Crawl index server
COMMON_CRAWL_INDEX_URL = "https://index.commoncrawl.org/CC-MAIN-2024-10-index"


class CommonCrawlService:
    """Queries Common Crawl index for historical public web presence."""

    async def lookup_url(self, target_url: str, limit: int = 5) -> list[dict[str, Any]]:
        """Bounded index search for URL in Common Crawl."""
        params = {
            "url": target_url,
            "output": "json",
            "limit": str(limit),
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(COMMON_CRAWL_INDEX_URL, params=params)
                if resp.status_code == 200:
                    lines = resp.text.strip().splitlines()
                    results = []
                    for line in lines:
                        if not line.strip():
                            continue
                        try:
                            item = json.loads(line)
                            results.append(item)
                        except json.JSONDecodeError:
                            pass
                    return results
        except Exception as err:
            logger.debug(f"Common Crawl index query failed for '{target_url}': {err}")

        return []

    async def record_snapshot(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        target_url: str,
        page_investigation_id: uuid.UUID | None = None,
        candidate_image_id: uuid.UUID | None = None,
    ) -> HistoricalSnapshot:
        """Lookup target URL in Common Crawl index and persist HistoricalSnapshot record."""
        records = await self.lookup_url(target_url, limit=5)

        if records:
            top = records[0]
            ts_str = top.get("timestamp")
            dt = None
            if ts_str and len(ts_str) >= 14:
                try:
                    dt = datetime.strptime(ts_str[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    dt = None

            snapshot = HistoricalSnapshot(
                page_investigation_id=page_investigation_id,
                candidate_image_id=candidate_image_id,
                organization_id=organization_id,
                source=HistoricalSource.COMMON_CRAWL,
                target_url=target_url,
                capture_timestamp=dt,
                archive_url=top.get("filename"),
                status=SnapshotStatus.OBSERVED,
                digest=top.get("digest"),
                metadata_json={"total_index_hits": len(records), "records": records},
            )
        else:
            snapshot = HistoricalSnapshot(
                page_investigation_id=page_investigation_id,
                candidate_image_id=candidate_image_id,
                organization_id=organization_id,
                source=HistoricalSource.COMMON_CRAWL,
                target_url=target_url,
                capture_timestamp=None,
                archive_url=None,
                status=SnapshotStatus.NOT_OBSERVED,
                digest=None,
                metadata_json={"reason": "NO_INDEX_RECORDS_RETURNED"},
            )

        session.add(snapshot)
        await session.flush()

        return snapshot


commoncrawl_service = CommonCrawlService()
