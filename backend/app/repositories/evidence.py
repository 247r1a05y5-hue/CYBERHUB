"""Evidence repository."""
from __future__ import annotations

from typing import List, Optional, Tuple
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import Analysis
from app.models.evidence import Evidence, EvidenceType
from app.models.incident import Incident
from app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    model = Evidence

    async def list_by_parent(
        self,
        organization_id: uuid.UUID,
        analysis_id: Optional[uuid.UUID] = None,
        incident_id: Optional[uuid.UUID] = None,
        evidence_type: Optional[EvidenceType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Evidence], int]:
        stmt = select(Evidence).options(selectinload(Evidence.uploaded_by))
        
        # Scoped to parent's organization via join or explicit filter
        if analysis_id is not None:
            stmt = stmt.join(Analysis, Evidence.analysis_id == Analysis.id).where(
                Analysis.organization_id == organization_id,
                Evidence.analysis_id == analysis_id,
            )
        elif incident_id is not None:
            stmt = stmt.join(Incident, Evidence.incident_id == Incident.id).where(
                Incident.organization_id == organization_id,
                Evidence.incident_id == incident_id,
            )
        else:
            # Union/Or query for both
            stmt = (
                stmt.outerjoin(Analysis, Evidence.analysis_id == Analysis.id)
                .outerjoin(Incident, Evidence.incident_id == Incident.id)
                .where(
                    (Analysis.organization_id == organization_id)
                    | (Incident.organization_id == organization_id)
                )
            )

        if evidence_type is not None:
            stmt = stmt.where(Evidence.evidence_type == evidence_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(desc(Evidence.created_at)).offset(offset).limit(limit)
        items_res = await self.session.execute(stmt)
        return list(items_res.scalars().all()), total

    async def get_by_id_and_org(
        self, evidence_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Optional[Evidence]:
        stmt = (
            select(Evidence)
            .outerjoin(Analysis, Evidence.analysis_id == Analysis.id)
            .outerjoin(Incident, Evidence.incident_id == Incident.id)
            .where(
                Evidence.id == evidence_id,
                (Analysis.organization_id == organization_id)
                | (Incident.organization_id == organization_id),
            )
            .options(selectinload(Evidence.uploaded_by))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
