"""Report repository."""
from __future__ import annotations

from typing import List, Optional, Tuple
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.report import Report, ReportStatus
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    model = Report

    async def get_with_details(
        self, report_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Optional[Report]:
        stmt = (
            select(Report)
            .options(selectinload(Report.created_by))
            .where(
                Report.id == report_id,
                Report.organization_id == organization_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: uuid.UUID,
        incident_id: Optional[uuid.UUID] = None,
        analysis_id: Optional[uuid.UUID] = None,
        status: Optional[ReportStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Report], int]:
        stmt = select(Report).where(Report.organization_id == organization_id)
        count_stmt = select(func.count(Report.id)).where(Report.organization_id == organization_id)

        if incident_id is not None:
            stmt = stmt.where(Report.incident_id == incident_id)
            count_stmt = count_stmt.where(Report.incident_id == incident_id)
        if analysis_id is not None:
            stmt = stmt.where(Report.analysis_id == analysis_id)
            count_stmt = count_stmt.where(Report.analysis_id == analysis_id)
        if status is not None:
            stmt = stmt.where(Report.status == status)
            count_stmt = count_stmt.where(Report.status == status)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            stmt.options(selectinload(Report.created_by))
            .order_by(desc(Report.created_at))
            .offset(offset)
            .limit(limit)
        )
        items_res = await self.session.execute(stmt)
        return list(items_res.scalars().all()), total
