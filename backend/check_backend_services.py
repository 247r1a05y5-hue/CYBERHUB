import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
from app.core.config import settings

async def check():
    print("DATABASE_URL:", settings.database_url)
    print("STORAGE_PATH:", settings.STORAGE_PATH)
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("SELECT 1"))
            print("DB SUCCESS:", res.scalar())
    except Exception as e:
        print("DB ERROR:", type(e), e)

if __name__ == "__main__":
    asyncio.run(check())
