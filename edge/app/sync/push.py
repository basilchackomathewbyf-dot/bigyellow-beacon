"""Build gzip SyncDelta batches from the outbox and push to shore."""

from __future__ import annotations

import gzip
import logging
from datetime import UTC, datetime

from beacon_contract import new_id
from beacon_contract.enums import SyncEntity, SyncOp
from beacon_contract.sync import (
    MAX_BATCH_BYTES_GZ,
    MAX_EVENTS_PER_BATCH,
    PushResponse,
    SyncDelta,
    SyncEvent,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Outbox, SyncState
from app.sync.client import ShoreClient

logger = logging.getLogger("beacon.edge.sync")


def _row_to_event(row: Outbox) -> SyncEvent:
    entity = SyncEntity(row.entity)
    if entity == SyncEntity.TICKET:
        return SyncEvent(
            event_id=row.id,
            entity=entity,
            op=SyncOp(row.op),
            entity_id=row.entity_id,
            version=row.version,
            occurred_at=row.created_at,
            owned_fields=row.payload,
            payload=None,
        )
    return SyncEvent(
        event_id=row.id,
        entity=entity,
        op=SyncOp(row.op),
        entity_id=row.entity_id,
        version=row.version,
        occurred_at=row.created_at,
        owned_fields=None,
        payload=row.payload,
    )


def _severity_bucket(row: Outbox) -> int:
    """0 = high severity (4–5) first; 1 = everything else."""
    if row.entity == SyncEntity.TICKET.value:
        sev = int(row.payload.get("severity") or 0)
        return 0 if sev >= 4 else 1
    return 1


async def pending_outbox(session: AsyncSession) -> list[Outbox]:
    rows = list(
        (
            await session.execute(
                select(Outbox).where(Outbox.pushed_at.is_(None)).order_by(Outbox.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    rows.sort(key=lambda r: (_severity_bucket(r), r.created_at))
    return rows


def _build_batch(
    rows: list[Outbox], vessel_id: str
) -> tuple[SyncDelta, bytes, list[Outbox]] | None:
    if not rows:
        return None
    chosen: list[Outbox] = []
    events: list[SyncEvent] = []
    body_gz = b""
    for row in rows:
        if len(events) >= MAX_EVENTS_PER_BATCH:
            break
        try:
            ev = _row_to_event(row)
        except Exception:
            logger.exception("outbox_skip_invalid event_id=%s", row.id)
            continue
        trial = events + [ev]
        delta = SyncDelta(
            vessel_id=vessel_id,
            batch_id=new_id(),
            events=trial,
        )
        raw = delta.model_dump_json().encode("utf-8")
        gz = gzip.compress(raw, compresslevel=6)
        if chosen and len(gz) > MAX_BATCH_BYTES_GZ:
            break
        chosen.append(row)
        events = trial
        body_gz = gz
        if len(gz) > MAX_BATCH_BYTES_GZ:
            break
    if not events:
        return None
    delta = SyncDelta(vessel_id=vessel_id, batch_id=new_id(), events=events)
    body_gz = gzip.compress(delta.model_dump_json().encode("utf-8"), compresslevel=6)
    return delta, body_gz, chosen


async def push_outbox(
    session: AsyncSession,
    *,
    state: SyncState,
    client: ShoreClient,
    vessel_id: str,
) -> int:
    """Push one batch. Returns gzip byte size (0 if nothing pushed)."""
    rows = await pending_outbox(session)
    built = _build_batch(rows, vessel_id)
    if built is None:
        return 0
    delta, body_gz, chosen = built
    resp = await client.push(body_gz)
    if resp.status_code >= 400:
        logger.warning("push_failed status=%s body=%s", resp.status_code, resp.text[:200])
        for row in chosen:
            row.attempts = int(row.attempts or 0) + 1
        await session.commit()
        raise RuntimeError(f"push failed: {resp.status_code}")

    push_resp = PushResponse.model_validate(resp.json())
    now = datetime.now(UTC)
    ack_by_id = {a.event_id: a for a in push_resp.acks}
    for row in chosen:
        ack = ack_by_id.get(row.id)
        if ack is None:
            row.attempts = int(row.attempts or 0) + 1
            continue
        if ack.status in ("applied", "duplicate"):
            row.pushed_at = now
        else:
            row.attempts = int(row.attempts or 0) + 1
            logger.warning("push_rejected event_id=%s err=%s", row.id, ack.error)

    state.last_push_at = now
    state.last_push_bytes_gz = len(body_gz)
    await session.commit()
    logger.info(
        "push_ok batch_id=%s events=%s bytes_gz=%s",
        delta.batch_id,
        len(chosen),
        len(body_gz),
    )
    return len(body_gz)
