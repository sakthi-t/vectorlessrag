import asyncio
import re
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

from alembic import context

from app.config import settings
from app.db.base import Base
from app.models.user import User  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.chunk import Chunk  # noqa: F401
from app.models.document_tree import DocumentTree  # noqa: F401
from app.models.bm25_index import BM25Stats  # noqa: F401
from app.models.chat import ChatSession, ChatMessage  # noqa: F401

config = context.config

target_metadata = Base.metadata


def to_asyncpg_url(url: str) -> str:
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    url = re.sub(r"[&?]sslmode=\w+", "", url)
    url = re.sub(r"[&?]channel_binding=\w+", "", url)
    if "?" in url:
        url += "&ssl=require"
    else:
        url += "?ssl=require"
    return url


def run_migrations_offline() -> None:
    url = to_asyncpg_url(settings.DATABASE_URL)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: AsyncConnection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = to_asyncpg_url(settings.DATABASE_URL)
    engine = create_async_engine(url, echo=False)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
