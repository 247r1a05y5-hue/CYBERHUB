import asyncio
from sqlalchemy import text
from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
import app.models
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.core.security import hash_password
from sqlalchemy import select

async def init():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA synchronous=NORMAL;"))
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Organization))
        org = res.scalars().first()
        if not org:
            org = Organization(name="CyberHub Defense Org")
            session.add(org)
            await session.flush()

            admin = User(
                email="admin@cyber.local",
                hashed_password=hash_password("Admin1234!"),
                full_name="System Administrator",
                role=UserRole.ADMIN,
                organization_id=org.id,
                is_active=True,
            )
            analyst = User(
                email="analyst@cyberhub.security",
                hashed_password=hash_password("Password123!"),
                full_name="Lead Analyst",
                role=UserRole.ANALYST,
                organization_id=org.id,
                is_active=True,
            )
            session.add_all([admin, analyst])
            await session.commit()
            print("Default users seeded.")
        else:
            print("Org already exists:", org.name)

if __name__ == "__main__":
    asyncio.run(init())
