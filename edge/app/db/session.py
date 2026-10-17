from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None) -> AsyncEngine:
    global _engine, async_session_factory
    url = database_url or get_settings().database_url
    _engine = create_async_engine(url, pool_pre_ping=True)
    async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        return init_engine()
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_factory is None:
        init_engine()
    assert async_session_factory is not None
    async with async_session_factory() as session:
        yield session
