"""Postgres advisory lock so worker and POST /sync/now never overlap."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Stable key for beacon sync cycles (arbitrary int64).
ADVISORY_LOCK_KEY = 942_007_001


@asynccontextmanager
async def sync_advisory_lock(session: AsyncSession) -> AsyncIterator[bool]:
    """Try to acquire; yields True if held. Always unlocks on exit if acquired."""
    got = (
        await session.execute(
            text("SELECT pg_try_advisory_lock(:k)"), {"k": ADVISORY_LOCK_KEY}
        )
    ).scalar()
    held = bool(got)
    try:
        yield held
    finally:
        if held:
            await session.execute(
                text("SELECT pg_advisory_unlock(:k)"), {"k": ADVISORY_LOCK_KEY}
            )
            await session.commit()
