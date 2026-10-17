"""GET /api/v1/events — SSE hub (M2).

# DECISION: Authenticate in a short-lived DB session, then stream without holding
a connection open (StreamingResponse would otherwise pin a session for the life
of the SSE connection).
"""

from __future__ import annotations

import asyncio
import time
from typing import Annotated

from beacon_contract.events import crew_channel, master_channel, vessel_channel
from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse

from app.auth.deps import AuthPrincipal, resolve_principal
from app.db import session as db_session
from app.events.hub import PING_INTERVAL_S, get_hub

router = APIRouter(tags=["events"])

_POLL_S = 1.0


def _channels_for(principal: AuthPrincipal) -> list[str]:
    vessel = principal.vessel_id
    if principal.role == "master":
        return [master_channel(vessel), vessel_channel(vessel)]
    return [crew_channel(principal.crew_id), vessel_channel(vessel)]


@router.get("/events")
async def events(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Query()] = None,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    if db_session.async_session_factory is None:
        db_session.init_engine()
    factory = db_session.async_session_factory
    assert factory is not None

    async with factory() as session:
        principal = await resolve_principal(
            request, session, authorization=authorization, access_token=access_token
        )

    channels = _channels_for(principal)
    hub = get_hub()
    queue = hub.subscribe(channels)

    async def stream():
        last_ping = time.monotonic()
        try:
            for msg in hub.replay_since(channels, last_event_id):
                if await request.is_disconnected():
                    return
                yield msg.encode()

            while True:
                if await request.is_disconnected():
                    return
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_POLL_S)
                except TimeoutError:
                    if time.monotonic() - last_ping >= PING_INTERVAL_S:
                        yield ": ping\n\n"
                        last_ping = time.monotonic()
                    continue
                if item is None:
                    break
                yield item.encode()
        finally:
            hub.unsubscribe(channels, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
