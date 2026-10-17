"""Idempotency-Key replay for write routes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Idempotency


async def get_replay(
    session: AsyncSession, *, key: str | None, route: str, crew_id: str
) -> dict[str, Any] | None:
    if not key:
        return None
    row = await session.get(Idempotency, key)
    if row is None:
        return None
    if row.route != route or row.crew_id != crew_id:
        return None
    return row.response


async def store_replay(
    session: AsyncSession,
    *,
    key: str | None,
    route: str,
    crew_id: str,
    response: dict[str, Any],
) -> None:
    if not key:
        return
    existing = await session.get(Idempotency, key)
    if existing is not None:
        return
    session.add(
        Idempotency(key=key, route=route, crew_id=crew_id, response=response)
    )
