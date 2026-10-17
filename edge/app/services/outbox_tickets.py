"""Build scrubbed ticket / action outbox SyncEvents."""

from __future__ import annotations

from datetime import UTC, datetime

from beacon_contract import collapse_rank_band, new_id, reporter_ref, scrub_text
from beacon_contract.enums import (
    HazardType,
    IsmCategory,
    OnboardStatus,
    RankBand,
    Severity,
    SyncEntity,
    SyncOp,
)
from beacon_contract.sync import (
    SyncEvent,
    TicketActionPayload,
    TicketEdgeFields,
    TicketMessagePayload,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Crew, Outbox, Ticket, TicketAction, TicketMedia, TicketMessage


async def _roster_names(session: AsyncSession, vessel_id: str) -> list[str]:
    rows = (
        await session.execute(select(Crew.display_name).where(Crew.vessel_id == vessel_id))
    ).scalars().all()
    return list(rows)


async def _band_size(session: AsyncSession, vessel_id: str, rank_band: str) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Crew)
        .where(
            Crew.vessel_id == vessel_id,
            Crew.rank_band == rank_band,
            Crew.active.is_(True),
        )
    )
    return int(result.scalar_one())


async def build_ticket_edge_fields(
    session: AsyncSession,
    *,
    ticket: Ticket,
) -> TicketEdgeFields:
    settings = get_settings()
    names = await _roster_names(session, ticket.vessel_id)
    band = RankBand(ticket.rank_band)
    size = await _band_size(session, ticket.vessel_id, ticket.rank_band)
    collapsed = collapse_rank_band(band, size)

    media_count = int(
        (
            await session.execute(
                select(func.count())
                .select_from(TicketMedia)
                .where(TicketMedia.ticket_id == ticket.id, TicketMedia.kind == "photo")
            )
        ).scalar_one()
    )

    return TicketEdgeFields(
        ticket_no=ticket.ticket_no,
        vessel_id=ticket.vessel_id,
        reporter_ref=ticket.reporter_ref
        or reporter_ref(settings.vessel_secret, ticket.reporter_crew_id, ticket.id),
        rank_band=collapsed,
        title_en=scrub_text(ticket.title_en, names) or ticket.title_en,
        description_en=scrub_text(ticket.description_en, names) or ticket.description_en,
        description_original=scrub_text(ticket.description_original, names),
        original_language=ticket.original_language,
        location_on_board=scrub_text(ticket.location_on_board, names)
        or ticket.location_on_board
        or "",
        hazard_type=HazardType(ticket.hazard_type),
        ism_category=IsmCategory(ticket.ism_category),
        severity=Severity(ticket.severity),
        immediate_action=scrub_text(ticket.immediate_action, names),
        occurred_at=ticket.occurred_at,
        created_at=ticket.created_at,
        onboard_status=OnboardStatus(ticket.onboard_status),
        media_count=media_count,
    )


def _add_outbox(session: AsyncSession, event: SyncEvent) -> None:
    # Ticket events store owned_fields in the payload column; others store payload.
    body = event.owned_fields if event.entity == SyncEntity.TICKET else (event.payload or {})
    session.add(
        Outbox(
            id=event.event_id,
            entity=event.entity.value,
            entity_id=event.entity_id,
            op=event.op.value,
            payload=body or {},
            version=event.version,
            created_at=event.occurred_at,
            attempts=0,
        )
    )


async def enqueue_ticket_insert(session: AsyncSession, *, ticket: Ticket) -> SyncEvent:
    fields = await build_ticket_edge_fields(session, ticket=ticket)
    event = SyncEvent(
        event_id=new_id(),
        entity=SyncEntity.TICKET,
        op=SyncOp.INSERT,
        entity_id=ticket.id,
        version=ticket.version or 1,
        occurred_at=ticket.created_at or datetime.now(UTC),
        owned_fields=fields.model_dump(mode="json"),
        payload=None,
    )
    _add_outbox(session, event)
    return event


async def enqueue_ticket_upsert(session: AsyncSession, *, ticket: Ticket) -> SyncEvent:
    ticket.version = int(ticket.version or 1) + 1
    fields = await build_ticket_edge_fields(session, ticket=ticket)
    event = SyncEvent(
        event_id=new_id(),
        entity=SyncEntity.TICKET,
        op=SyncOp.UPSERT,
        entity_id=ticket.id,
        version=ticket.version,
        occurred_at=datetime.now(UTC),
        owned_fields=fields.model_dump(mode="json"),
        payload=None,
    )
    _add_outbox(session, event)
    return event


async def enqueue_ticket_action(
    session: AsyncSession, *, action: TicketAction
) -> SyncEvent:
    payload = TicketActionPayload(
        action_id=action.id,
        ticket_id=action.ticket_id,
        actor_role="master",
        action_type=action.action_type,  # type: ignore[arg-type]
        text=action.text,
        responsible_rank=action.responsible_rank,
        due_at=action.due_at,
        created_at=action.created_at,
    )
    event = SyncEvent(
        event_id=new_id(),
        entity=SyncEntity.TICKET_ACTION,
        op=SyncOp.INSERT,
        entity_id=action.id,
        version=1,
        occurred_at=action.created_at or datetime.now(UTC),
        owned_fields=None,
        payload=payload.model_dump(mode="json"),
    )
    _add_outbox(session, event)
    return event


async def enqueue_ticket_message(
    session: AsyncSession, *, message: TicketMessage, vessel_id: str
) -> SyncEvent:
    """Reporter → shore only. Body scrubbed against vessel roster names."""
    names = await _roster_names(session, vessel_id)
    scrubbed = scrub_text(message.body, names) or message.body
    if message.sender != "reporter":
        raise ValueError("only reporter messages are written to the outbox")
    payload = TicketMessagePayload(
        message_id=message.id,
        ticket_id=message.ticket_id,
        sender="reporter",
        body=scrubbed,
        created_at=message.created_at,
    )
    event = SyncEvent(
        event_id=new_id(),
        entity=SyncEntity.TICKET_MESSAGE,
        op=SyncOp.INSERT,
        entity_id=message.id,
        version=1,
        occurred_at=message.created_at or datetime.now(UTC),
        owned_fields=None,
        payload=payload.model_dump(mode="json"),
    )
    _add_outbox(session, event)
    return event
