"""Master ticket views — reporter_name only when share_name_with_master."""

from __future__ import annotations

from beacon_contract.edge_api import MasterTicket, MediaRef, TicketActionView
from beacon_contract.enums import (
    ActionType,
    ActorRole,
    HazardType,
    IsmCategory,
    MediaKind,
    OnboardStatus,
    RankBand,
    Severity,
    ShoreStatus,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Crew, Ticket, TicketAction, TicketMedia


def _media_refs(media: list[TicketMedia]) -> list[MediaRef]:
    return [
        MediaRef(
            media_id=m.id,
            kind=MediaKind.PHOTO if m.kind == "photo" else MediaKind.AUDIO,
            url=f"/api/v1/media/{m.id}",
        )
        for m in media
        if m.kind == "photo"
    ]


def _action_views(actions: list[TicketAction]) -> list[TicketActionView]:
    return [
        TicketActionView(
            action_id=a.id,
            ticket_id=a.ticket_id,
            actor_role=ActorRole(a.actor_role),
            action_type=ActionType(a.action_type),
            text=a.text,
            responsible_rank=a.responsible_rank,
            due_at=a.due_at,
            created_at=a.created_at,
        )
        for a in sorted(actions, key=lambda x: x.created_at)
    ]


def ticket_to_master_view(
    ticket: Ticket,
    reporter_name: str | None,
    *,
    media: list[TicketMedia] | None = None,
    actions: list[TicketAction] | None = None,
) -> MasterTicket:
    """Build MasterTicket. Never include reporter identity unless opted in."""
    name = reporter_name if ticket.share_name_with_master else None
    media_list = media if media is not None else list(getattr(ticket, "media", []) or [])
    action_list = actions if actions is not None else list(getattr(ticket, "actions", []) or [])
    return MasterTicket(
        ticket_id=ticket.id,
        ticket_no=ticket.ticket_no,
        title_en=ticket.title_en,
        description_en=ticket.description_en,
        description_original=ticket.description_original,
        original_language=ticket.original_language,
        location_on_board=ticket.location_on_board or "",
        hazard_type=HazardType(ticket.hazard_type),
        ism_category=IsmCategory(ticket.ism_category),
        severity=Severity(ticket.severity),
        immediate_action=ticket.immediate_action,
        occurred_at=ticket.occurred_at,
        created_at=ticket.created_at,
        onboard_status=OnboardStatus(ticket.onboard_status),
        shore_status=ShoreStatus(ticket.shore_status),
        rank_band=RankBand(ticket.rank_band),
        reporter_name=name,
        media=_media_refs(media_list),
        actions=_action_views(action_list),
    )


async def _load_tickets(
    session: AsyncSession,
    *,
    onboard_status: str | None = None,
    severity: int | None = None,
    ticket_id: str | None = None,
) -> list[Ticket]:
    q = select(Ticket).options(
        selectinload(Ticket.media),
        selectinload(Ticket.actions),
    )
    if ticket_id:
        q = q.where(Ticket.id == ticket_id)
    if onboard_status:
        q = q.where(Ticket.onboard_status == onboard_status)
    if severity is not None:
        q = q.where(Ticket.severity == severity)
    q = q.order_by(Ticket.created_at.desc())
    return list((await session.execute(q)).scalars().unique().all())


async def list_master_tickets(
    session: AsyncSession,
    *,
    onboard_status: str | None = None,
    severity: int | None = None,
) -> list[MasterTicket]:
    tickets = await _load_tickets(
        session, onboard_status=onboard_status, severity=severity
    )

    crew_ids = {t.reporter_crew_id for t in tickets if t.share_name_with_master}
    names: dict[str, str] = {}
    if crew_ids:
        rows = (await session.execute(select(Crew).where(Crew.id.in_(crew_ids)))).scalars().all()
        names = {c.id: c.display_name for c in rows}

    return [
        ticket_to_master_view(
            t,
            names.get(t.reporter_crew_id) if t.share_name_with_master else None,
            media=list(t.media),
            actions=list(t.actions),
        )
        for t in tickets
    ]


async def get_master_ticket(session: AsyncSession, ticket_id: str) -> MasterTicket | None:
    tickets = await _load_tickets(session, ticket_id=ticket_id)
    if not tickets:
        return None
    t = tickets[0]
    name: str | None = None
    if t.share_name_with_master:
        crew = await session.get(Crew, t.reporter_crew_id)
        name = crew.display_name if crew else None
    return ticket_to_master_view(t, name, media=list(t.media), actions=list(t.actions))
