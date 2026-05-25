import re
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings


def _build_asyncpg_url(url: str) -> str:
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = re.sub(r"[&?]sslmode=\w+", "", url)
    url = re.sub(r"[&?]channel_binding=\w+", "", url)
    if "?" in url:
        url += "&ssl=require"
    else:
        url += "?ssl=require"
    return url


engine = create_async_engine(_build_asyncpg_url(settings.DATABASE_URL), echo=False, pool_size=5, max_overflow=10)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
