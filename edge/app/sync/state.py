"""SyncState helpers + effective link status."""

from __future__ import annotations

from beacon_contract.edge_api import SyncStatus
from beacon_contract.enums import LinkOverride, LinkStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import Outbox, SyncState, TicketMedia


async def get_or_create_sync_state(
    session: AsyncSession, *, settings: Settings | None = None
) -> SyncState:
    settings = settings or get_settings()
    row = await session.get(SyncState, settings.vessel_id)
    if row is None:
        row = SyncState(
            vessel_id=settings.vessel_id,
            link_status=LinkStatus.DOWN.value,
            link_override=settings.link_override,
        )
        session.add(row)
        await session.flush()
    return row


def effective_link(state: SyncState, *, probe_up: bool | None = None) -> LinkStatus:
    ov = LinkOverride(state.link_override)
    if ov == LinkOverride.UP:
        return LinkStatus.UP
    if ov == LinkOverride.DOWN:
        return LinkStatus.DOWN
    if probe_up is None:
        # Fall back to last recorded probe-derived status.
        try:
            return LinkStatus(state.link_status)
        except ValueError:
            return LinkStatus.UNKNOWN
    return LinkStatus.UP if probe_up else LinkStatus.DOWN


async def refresh_pending_counts(session: AsyncSession, state: SyncState) -> None:
    pending_events = int(
        (
            await session.execute(
                select(func.count()).select_from(Outbox).where(Outbox.pushed_at.is_(None))
            )
        ).scalar_one()
    )
    pending_media = int(
        (
            await session.execute(
                select(func.count())
                .select_from(TicketMedia)
                .where(TicketMedia.kind == "photo", TicketMedia.synced.is_(False))
            )
        ).scalar_one()
    )
    state.pending_events = pending_events
    state.pending_media = pending_media


async def to_sync_status(
    session: AsyncSession, state: SyncState, *, probe_up: bool | None = None
) -> SyncStatus:
    await refresh_pending_counts(session, state)
    link = effective_link(state, probe_up=probe_up)
    return SyncStatus(
        link=link,
        override=LinkOverride(state.link_override),
        last_probe_at=state.last_probe_at,
        last_push_at=state.last_push_at,
        last_pull_at=state.last_pull_at,
        pending_events=state.pending_events,
        pending_media=state.pending_media,
        last_push_bytes_gz=state.last_push_bytes_gz,
    )
