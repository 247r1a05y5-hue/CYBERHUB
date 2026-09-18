"""Wayback Machine CDX Historical Archive Service.

Queries the Internet Archive CDX Server API to retrieve public historical captures.
Preserves explicit semantics:
- Capture found -> OBSERVED (with capture timestamp & archive URL)
- No capture found -> NOT_OBSERVED (preserves uncertainty; never asserts "never existed" or "was deleted")
"""
from __future__ import annotations

import logging
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation_record import HistoricalSnapshot, HistoricalSource, SnapshotStatus

logger = logging.getLogger(__name__)

WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"


class WaybackService:
    """Queries Wayback Machine CDX API for historical page and image presence."""

    async def lookup_url(self, target_url: str, limit: int = 5) -> list[dict[str, Any]]:
        """Query CDX API for snapshot history of a URL."""
        params = {
            "url": target_url,
            "output": "json",
            "limit": str(limit),
            "fl": "timestamp,original,mimetype,statuscode,digest",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(WAYBACK_CDX_URL, params=params)
                if resp.status_code == 200:
                    rows = resp.json()
                    if len(rows) > 1:
                        headers = rows[0]
                        snapshots = []
                        for row in rows[1:]:
                            entry = dict(zip(headers, row))
                            ts_str = entry.get("timestamp")
                            archive_url = f"https://web.archive.org/web/{ts_str}/{target_url}" if ts_str else None
                            entry["archive_url"] = archive_url
                            snapshots.append(entry)
                        return snapshots
        except Exception as err:
            logger.debug(f"Wayback CDX query failed for '{target_url}': {err}")

        return []

    async def record_snapshot(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        target_url: str,
        page_investigation_id: uuid.UUID | None = None,
        candidate_image_id: uuid.UUID | None = None,
    ) -> HistoricalSnapshot:
        """Lookup target URL on Wayback Machine and persist HistoricalSnapshot record."""
        snapshots = await self.lookup_url(target_url, limit=5)

        if snapshots:
            top = snapshots[0]
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
                source=HistoricalSource.WAYBACK,
                target_url=target_url,
                capture_timestamp=dt,
                archive_url=top.get("archive_url"),
                status=SnapshotStatus.OBSERVED,
                digest=top.get("digest"),
                metadata_json={"total_captures": len(snapshots), "captures": snapshots},
            )
        else:
            snapshot = HistoricalSnapshot(
                page_investigation_id=page_investigation_id,
                candidate_image_id=candidate_image_id,
                organization_id=organization_id,
                source=HistoricalSource.WAYBACK,
                target_url=target_url,
                capture_timestamp=None,
                archive_url=None,
                status=SnapshotStatus.NOT_OBSERVED,
                digest=None,
                metadata_json={"reason": "NO_CAPTURES_RETURNED_BY_CDX"},
            )

        session.add(snapshot)
        await session.flush()

        return snapshot


wayback_service = WaybackService()
