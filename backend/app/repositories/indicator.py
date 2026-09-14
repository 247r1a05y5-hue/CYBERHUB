"""Indicator repository."""
from __future__ import annotations

from typing import List, Optional, Tuple
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.indicator import Indicator, IndicatorType
from app.repositories.base import BaseRepository


class IndicatorRepository(BaseRepository[Indicator]):
    model = Indicator

    async def list_by_org(
        self,
        organization_id: uuid.UUID,
        indicator_type: Optional[IndicatorType] = None,
        query_text: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Indicator], int]:
        stmt = select(Indicator).where(Indicator.organization_id == organization_id)
        count_stmt = select(func.count(Indicator.id)).where(Indicator.organization_id == organization_id)

        if indicator_type:
            stmt = stmt.where(Indicator.indicator_type == indicator_type)
            count_stmt = count_stmt.where(Indicator.indicator_type == indicator_type)
        if query_text:
            stmt = stmt.where(Indicator.value.ilike(f"%{query_text}%"))
            count_stmt = count_stmt.where(Indicator.value.ilike(f"%{query_text}%"))

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(desc(Indicator.created_at)).offset(offset).limit(limit)
        items_res = await self.session.execute(stmt)
        return list(items_res.scalars().all()), total

    async def get_by_analysis(
        self, organization_id: uuid.UUID, analysis_id: uuid.UUID
    ) -> List[Indicator]:
        stmt = (
            select(Indicator)
            .where(
                Indicator.organization_id == organization_id,
                Indicator.analysis_id == analysis_id,
            )
            .order_by(desc(Indicator.confidence))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
