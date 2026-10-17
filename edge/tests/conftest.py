"""Pytest fixtures — Postgres via BEACON_DATABASE_URL (compose db on host :5433)."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Defaults for local compose (host port 5433 → container 5432)
os.environ.setdefault(
    "BEACON_DATABASE_URL",
    "postgresql+asyncpg://beacon:beacon@localhost:5433/beacon",
)
os.environ.setdefault("BEACON_EDGE_SECRET", "test-secret-at-least-32-bytes-long!!")
os.environ.setdefault("BEACON_MASTER_USERNAME", "master")
os.environ.setdefault("BEACON_MASTER_PIN", "1234")
os.environ.setdefault("BEACON_SO_USERNAME", "safety")
os.environ.setdefault("BEACON_SO_PIN", "5678")
os.environ.setdefault("BEACON_VESSEL_ID", "VSL-DEMO01")
os.environ.setdefault("BEACON_VESSEL_NAME", "MV Demo Star")
os.environ.setdefault("BEACON_EDGE_PUBLIC_URL", "http://192.168.1.10:8080")
_edge_root = Path(__file__).resolve().parent.parent
_contracts = _edge_root.parent / "contracts"
os.environ.setdefault("BEACON_DATA_DIR", str(_edge_root / "data-test"))
os.environ.setdefault("BEACON_CONTRACTS_DIR", str(_contracts))

from app.auth.staff import ensure_staff_seeded, reset_lockouts  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import models  # noqa: F401, E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest_asyncio.fixture
async def engine():
    get_settings.cache_clear()
    settings = get_settings()
    eng = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(
                "TRUNCATE devices, staff_users, pairing_codes, near_misses, "
                "near_miss_media, near_miss_clarifications, checkin_scores, "
                "help_requests, notices, notice_translations, notice_acks, "
                "fleet_alerts, briefs, outbox, sync_state, docs, doc_chunks, "
                "translations_cache, idempotency RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
        await ensure_staff_seeded(session)
        await session.commit()
        reset_lockouts()
        yield session


@pytest_asyncio.fixture
async def client(engine, session) -> AsyncGenerator[AsyncClient, None]:
    get_settings.cache_clear()
    application = create_app()

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as s:
            yield s

    application.dependency_overrides[get_session] = _override

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    application.dependency_overrides.clear()
