"""Pytest fixtures — Postgres via BEACON_DATABASE_URL (compose db on host :5433)."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_edge_root = Path(__file__).resolve().parent.parent
_repo_root = _edge_root.parent
_roster = _repo_root / "seed" / "crew_v-0007.json"

os.environ.setdefault(
    "BEACON_DATABASE_URL",
    "postgresql+asyncpg://beacon:beacon@localhost:5433/beacon",
)
os.environ.setdefault("BEACON_JWT_SECRET", "test-secret-at-least-32-bytes-long!!")
os.environ.setdefault("BEACON_VESSEL_ID", "v-0007")
os.environ.setdefault("BEACON_VESSEL_CODE", "0007")
os.environ.setdefault("BEACON_VESSEL_NAME", "MV Demo Star")
os.environ.setdefault("BEACON_VESSEL_SECRET", "demo-vessel-secret-v-0007")
os.environ.setdefault("BEACON_EDGE_URL", "https://beacon.ship.local:8443")
os.environ.setdefault("BEACON_AI", "fake")
os.environ.setdefault("BEACON_AI_FAKE_DELAY", "0")
os.environ.setdefault("BEACON_DATA_DIR", str(_edge_root / "data-test"))
os.environ.setdefault("BEACON_ROSTER_FILE", str(_roster))
os.environ.setdefault("BEACON_K_ANON", "5")

from app.auth.deps import reset_revoke_cache  # noqa: E402
from app.auth.rate_limit import reset_rate_limits  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import models  # noqa: F401, E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.events.hub import get_hub  # noqa: E402
from app.main import create_app  # noqa: E402
from app.seed import seed_roster  # noqa: E402

_TRUNCATE = """
TRUNCATE
  ticket_messages, ticket_actions, ticket_media, tickets, ticket_seq,
  learning_acks, learning_stats, learning_media, learnings,
  checkins, checkin_aggregates,
  anchor_reactions, anchor_stats, anchor_cards,
  welfare_requests, outbox, sync_state, inbox,
  drafts, idempotency, rail_hits, briefs, fleet_alerts,
  pairing_codes, devices, crew, vessels
RESTART IDENTITY CASCADE
"""


@pytest_asyncio.fixture
async def engine():
    get_settings.cache_clear()
    settings = get_settings()
    eng = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(text(_TRUNCATE))
        await session.commit()
        await seed_roster(session)
        await session.commit()
        reset_rate_limits()
        reset_revoke_cache()
        get_hub().reset()
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


@pytest_asyncio.fixture
async def paired_master(client: AsyncClient, session: AsyncSession) -> dict:
    from app.auth.pairing import create_pairing_code

    plaintext, _row = await create_pairing_code(session, "c-0007-mst")
    await session.commit()
    pair = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": plaintext, "crew_id": "c-0007-mst", "pin": "123456"},
    )
    assert pair.status_code == 200, pair.text
    device_token = pair.json()["device_token"]
    login = await client.post(
        "/api/v1/auth/login",
        json={"device_token": device_token, "pin": "123456"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {
        "device_token": device_token,
        "access_token": token,
        "crew_id": "c-0007-mst",
        "headers": {"Authorization": f"Bearer {token}"},
        "device_id": pair.json()["device_id"],
    }


@pytest_asyncio.fixture
async def paired_crew(client: AsyncClient, paired_master: dict) -> dict:
    r = await client.post(
        "/api/v1/auth/pairing-codes",
        headers=paired_master["headers"],
        json={"crew_id": "c-0007-aru"},
    )
    assert r.status_code == 200, r.text
    code = r.json()["code"]
    pair = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": code, "crew_id": "c-0007-aru", "pin": "1234"},
    )
    assert pair.status_code == 200, pair.text
    device_token = pair.json()["device_token"]
    login = await client.post(
        "/api/v1/auth/login",
        json={"device_token": device_token, "pin": "1234"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {
        "device_token": device_token,
        "access_token": token,
        "crew_id": "c-0007-aru",
        "headers": {"Authorization": f"Bearer {token}"},
        "device_id": pair.json()["device_id"],
    }
