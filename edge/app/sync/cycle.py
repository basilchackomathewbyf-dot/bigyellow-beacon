"""One sync cycle: probe → push → media → pull → emit status."""

from __future__ import annotations

import logging

from beacon_contract.enums import LinkOverride, LinkStatus
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.events.emit import emit_sync_status
from app.sync.client import ShoreClient
from app.sync.lock import sync_advisory_lock
from app.sync.pull import pull_and_apply, upload_pending_media
from app.sync.push import push_outbox
from app.sync.state import (
    effective_link,
    get_or_create_sync_state,
    refresh_pending_counts,
    to_sync_status,
)

logger = logging.getLogger("beacon.edge.sync")

# Consecutive successful probes (worker process). 2 → UP in auto mode.
_probe_successes = 0


def reset_probe_streak() -> None:
    global _probe_successes
    _probe_successes = 0


async def run_sync_cycle(
    session: AsyncSession,
    *,
    settings: Settings | None = None,
    client: ShoreClient | None = None,
    force_probe: bool = True,
) -> dict:
    """
    Run one cycle under the advisory lock.
    Returns a summary dict (or {"skipped": "locked"} if lock not acquired).
    """
    global _probe_successes
    settings = settings or get_settings()
    owns_client = client is None
    client = client or ShoreClient(settings)

    try:
        async with sync_advisory_lock(session) as held:
            if not held:
                logger.info("sync_cycle_skipped reason=locked")
                return {"skipped": "locked"}

            state = await get_or_create_sync_state(session, settings=settings)

            probe_up: bool | None = None
            if force_probe:
                ok = await client.healthz()
                if ok:
                    _probe_successes += 1
                else:
                    _probe_successes = 0
                from datetime import UTC, datetime

                state.last_probe_at = datetime.now(UTC)
                auto_up = _probe_successes >= 2
                if LinkOverride(state.link_override) == LinkOverride.AUTO:
                    state.link_status = (
                        LinkStatus.UP.value if auto_up else LinkStatus.DOWN.value
                    )
                probe_up = auto_up
                await session.commit()

            link = effective_link(state, probe_up=probe_up)
            summary: dict = {
                "link": link.value,
                "pushed_bytes": 0,
                "pulled": 0,
                "media": 0,
            }

            if link != LinkStatus.UP:
                await refresh_pending_counts(session, state)
                await session.commit()
                status = await to_sync_status(session, state, probe_up=probe_up)
                emit_sync_status(status.model_dump(mode="json"), vessel_id=settings.vessel_id)
                summary["skipped"] = "link_down"
                return summary

            try:
                last_bytes = 0
                for _ in range(20):
                    n = await push_outbox(
                        session,
                        state=state,
                        client=client,
                        vessel_id=settings.vessel_id,
                    )
                    if not n:
                        break
                    last_bytes = n
                summary["pushed_bytes"] = last_bytes
                summary["media"] = await upload_pending_media(session, client=client)
                summary["pulled"] = await pull_and_apply(
                    session, state=state, client=client
                )
            except Exception:
                logger.exception("sync_cycle_error")
                await session.rollback()
                raise
            finally:
                state = await get_or_create_sync_state(session, settings=settings)
                status = await to_sync_status(session, state)
                await session.commit()
                emit_sync_status(status.model_dump(mode="json"), vessel_id=settings.vessel_id)

            return summary
    finally:
        if owns_client:
            await client.aclose()
