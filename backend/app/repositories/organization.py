"""Organization repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, id) -> Organization | None:
        return await self.session.get(Organization, id)

    async def create(
        self,
        *,
        name: str,
        slug: str,
        description: str | None = None,
    ) -> Organization:
        org = Organization(name=name, slug=slug, description=description)
        self.session.add(org)
        await self.session.flush()
        await self.session.refresh(org)
        return org

    async def list_all(self) -> list[Organization]:
        result = await self.session.execute(select(Organization))
        return list(result.scalars().all())
