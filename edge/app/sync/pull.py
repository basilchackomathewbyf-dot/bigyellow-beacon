"""Pull shore changes and apply them; upload pending photos."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from beacon_contract.sync import PullResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncState, TicketMedia
from app.sync.apply import apply_change
from app.sync.client import ShoreClient

logger = logging.getLogger("beacon.edge.sync")


async def upload_pending_media(
    session: AsyncSession, *, client: ShoreClient
) -> int:
    rows = list(
        (
            await session.execute(
                select(TicketMedia).where(
                    TicketMedia.kind == "photo", TicketMedia.synced.is_(False)
                )
            )
        )
        .scalars()
        .all()
    )
    n = 0
    for media in rows:
        if not media.local_path or not Path(media.local_path).is_file():
            continue
        data = Path(media.local_path).read_bytes()
        resp = await client.upload_media(media.id, data)
        if resp.status_code in (200, 201, 204):
            media.synced = True
            n += 1
        else:
            logger.warning(
                "media_upload_failed id=%s status=%s", media.id, resp.status_code
            )
    if n:
        await session.commit()
    return n


async def pull_and_apply(
    session: AsyncSession,
    *,
    state: SyncState,
    client: ShoreClient,
) -> int:
    """Pull until has_more=false. Returns number of changes applied."""
    applied = 0
    cursor = state.last_pull_cursor
    while True:
        resp = await client.pull(cursor=cursor, limit=200)
        if resp.status_code >= 400:
            logger.warning("pull_failed status=%s", resp.status_code)
            raise RuntimeError(f"pull failed: {resp.status_code}")
        body = PullResponse.model_validate(resp.json())
        for change in body.changes:
            await apply_change(session, change, client=client)
            applied += 1
        state.last_pull_cursor = body.next_cursor
        state.last_pull_at = datetime.now(UTC)
        await session.commit()
        cursor = body.next_cursor
        if not body.has_more:
            break
    if applied:
        logger.info("pull_ok changes=%s cursor=%s", applied, cursor)
    return applied
