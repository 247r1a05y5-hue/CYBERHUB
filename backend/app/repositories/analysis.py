"""Analysis repositories for managing analyses, inputs, and results."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import Analysis, AnalysisStatus
from app.models.analysis_input import AnalysisInput, InputType
from app.models.analysis_result import AnalysisResult, Severity, Verdict
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    model = Analysis

    async def get_with_details(
        self, analysis_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Optional[Analysis]:
        stmt = (
            select(Analysis)
            .options(
                selectinload(Analysis.input),
                selectinload(Analysis.result),
                selectinload(Analysis.alerts),
            )
            .where(
                Analysis.id == analysis_id,
                Analysis.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_content_hash(
        self, organization_id: uuid.UUID, content_hash: str
    ) -> Optional[Analysis]:
        stmt = (
            select(Analysis)
            .options(selectinload(Analysis.input), selectinload(Analysis.result))
            .where(
                Analysis.organization_id == organization_id,
                Analysis.content_hash == content_hash,
                Analysis.status != AnalysisStatus.failed,
            )
            .order_by(desc(Analysis.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: uuid.UUID,
        status: Optional[AnalysisStatus] = None,
        analyzer_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Analysis], int]:
        query = select(Analysis).where(Analysis.organization_id == organization_id)
        count_query = select(func.count(Analysis.id)).where(Analysis.organization_id == organization_id)

        if status is not None:
            query = query.where(Analysis.status == status)
            count_query = count_query.where(Analysis.status == status)
        if analyzer_type:
            query = query.where(Analysis.analyzer_type == analyzer_type)
            count_query = count_query.where(Analysis.analyzer_type == analyzer_type)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar_one()

        query = (
            query.options(selectinload(Analysis.result), selectinload(Analysis.input))
            .order_by(desc(Analysis.created_at))
            .offset(offset)
            .limit(limit)
        )
        items_res = await self.session.execute(query)
        return list(items_res.scalars().all()), total

    async def update_status(
        self,
        analysis_id: uuid.UUID,
        status: AnalysisStatus,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> Optional[Analysis]:
        values: Dict[str, Any] = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        if execution_time_ms is not None:
            values["execution_time_ms"] = execution_time_ms
        if job_id is not None:
            values["job_id"] = job_id
        if status in (AnalysisStatus.completed, AnalysisStatus.failed):
            values["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(Analysis)
            .where(Analysis.id == analysis_id)
            .values(**values)
            .returning(Analysis)
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.scalar_one_or_none()


class AnalysisInputRepository(BaseRepository[AnalysisInput]):
    model = AnalysisInput

    async def get_by_analysis_id(self, analysis_id: uuid.UUID) -> Optional[AnalysisInput]:
        stmt = select(AnalysisInput).where(AnalysisInput.analysis_id == analysis_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class AnalysisResultRepository(BaseRepository[AnalysisResult]):
    model = AnalysisResult

    async def get_by_analysis_id(self, analysis_id: uuid.UUID) -> Optional[AnalysisResult]:
        stmt = select(AnalysisResult).where(AnalysisResult.analysis_id == analysis_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
