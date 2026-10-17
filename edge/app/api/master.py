"""Minimal Master routes for M0 (full board lands in M2).

# DECISION: M0 ships GET /master/tickets only (empty/list + role gate) so
# privacy tests (crew → 403, reporter_name gating) stay green before M2.
"""

from __future__ import annotations

from typing import Annotated

from beacon_contract.edge_api import MasterTicket
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, require_role  # noqa: F401 — require_role("master")
from app.db.session import get_session
from app.services.master_tickets import list_master_tickets

router = APIRouter(prefix="/master", tags=["master"])


@router.get("/tickets", response_model=list[MasterTicket])
async def master_tickets(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
    onboard_status: str | None = None,
    severity: int | None = None,
) -> list[MasterTicket]:
    return await list_master_tickets(session, onboard_status=onboard_status, severity=severity)
