"""Master ticket views — reporter_name only when share_name_with_master."""

from __future__ import annotations

from beacon_contract.edge_api import MasterTicket
from beacon_contract.enums import (
    HazardType,
    IsmCategory,
    OnboardStatus,
    RankBand,
    Severity,
    ShoreStatus,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Crew, Ticket


def ticket_to_master_view(ticket: Ticket, reporter_name: str | None) -> MasterTicket:
    """Build MasterTicket. Never include reporter identity unless opted in."""
    name = reporter_name if ticket.share_name_with_master else None
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
    )


async def list_master_tickets(
    session: AsyncSession,
    *,
    onboard_status: str | None = None,
    severity: int | None = None,
) -> list[MasterTicket]:
    q = select(Ticket)
    if onboard_status:
        q = q.where(Ticket.onboard_status == onboard_status)
    if severity is not None:
        q = q.where(Ticket.severity == severity)
    q = q.order_by(Ticket.created_at.desc())
    tickets = list((await session.execute(q)).scalars().all())

    crew_ids = {t.reporter_crew_id for t in tickets if t.share_name_with_master}
    names: dict[str, str] = {}
    if crew_ids:
        rows = (await session.execute(select(Crew).where(Crew.id.in_(crew_ids)))).scalars().all()
        names = {c.id: c.display_name for c in rows}

    return [
        ticket_to_master_view(
            t, names.get(t.reporter_crew_id) if t.share_name_with_master else None
        )
        for t in tickets
    ]
