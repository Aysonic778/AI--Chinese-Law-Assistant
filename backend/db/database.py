from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import settings
from backend.db.models import Base

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def _migrate_columns() -> None:
    migrations = [
        "ALTER TABLE documents ADD COLUMN summary_text TEXT DEFAULT ''",
        "ALTER TABLE documents ADD COLUMN summary_chroma_id VARCHAR(100) DEFAULT ''",
        "ALTER TABLE messages ADD COLUMN conversation_id INTEGER",
    ]
    async with engine.begin() as conn:
        for statement in migrations:
            try:
                await conn.execute(text(statement))
            except Exception:
                pass


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_columns()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
