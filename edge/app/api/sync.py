"""GET /sync/status, POST /sync/now, POST /sync/override (M4)."""

from __future__ import annotations

from typing import Annotated, Literal

from beacon_contract.edge_api import SyncStatus
from beacon_contract.enums import LinkOverride
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, get_current_user, require_role
from app.config import get_settings
from app.db.session import get_session
from app.sync.cycle import run_sync_cycle
from app.sync.state import get_or_create_sync_state, to_sync_status

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncOverrideRequest(BaseModel):
    mode: Literal["auto", "up", "down"] = Field(..., description="Link override")


@router.get("/status", response_model=SyncStatus)
async def sync_status(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> SyncStatus:
    state = await get_or_create_sync_state(session)
    status = await to_sync_status(session, state)
    await session.commit()
    return status


@router.post("/now", response_model=SyncStatus)
async def sync_now(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
) -> SyncStatus:
    settings = get_settings()
    await run_sync_cycle(session, settings=settings, force_probe=True)
    state = await get_or_create_sync_state(session, settings=settings)
    return await to_sync_status(session, state)


@router.post("/override", response_model=SyncStatus)
async def sync_override(
    body: SyncOverrideRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
) -> SyncStatus:
    settings = get_settings()
    state = await get_or_create_sync_state(session, settings=settings)
    state.link_override = LinkOverride(body.mode).value
    # When forcing up/down, mirror into link_status for immediate status reads.
    if body.mode == "up":
        state.link_status = "UP"
    elif body.mode == "down":
        state.link_status = "DOWN"
    await session.commit()
    return await to_sync_status(session, state)
