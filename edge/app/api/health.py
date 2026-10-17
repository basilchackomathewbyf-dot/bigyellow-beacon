"""GET /api/v1/health."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncState
from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict:
    shore_link = "down"
    result = await session.execute(select(SyncState).where(SyncState.key == "link_mode"))
    link_mode = result.scalar_one_or_none()
    if link_mode and link_mode.value == "forced_down":
        shore_link = "down"
    else:
        ok = await session.execute(select(SyncState).where(SyncState.key == "last_link_ok_at"))
        ok_row = ok.scalar_one_or_none()
        if ok_row and ok_row.value:
            shore_link = "up"

    # E1: model server not yet running — report not ready.
    return {
        "status": "ok",
        "model_ready": False,
        "shore_link": shore_link,
        "edge_time": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
