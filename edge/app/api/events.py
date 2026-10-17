"""SSE hub stub — auth accepts Bearer or ?access_token= (full hub in M2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth.deps import AuthPrincipal, get_current_user

router = APIRouter(tags=["events"])


async def _ping_stream():
    yield ": ping\n\n"


@router.get("/events")
async def events(
    _principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> StreamingResponse:
    return StreamingResponse(_ping_stream(), media_type="text/event-stream")
