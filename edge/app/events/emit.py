"""Publish contract SSE events onto role channels."""

from __future__ import annotations

from datetime import datetime

from beacon_contract.enums import HazardType, OnboardStatus, Severity, ShoreStatus, SseEvent
from beacon_contract.events import (
    TicketNewData,
    TicketUpdatedData,
    crew_channel,
    master_channel,
)

from app.db.models import Ticket
from app.events.hub import get_hub


def emit_ticket_new(*, ticket: Ticket, vessel_id: str) -> None:
    data = TicketNewData(
        ticket_id=ticket.id,
        ticket_no=ticket.ticket_no,
        title_en=ticket.title_en,
        severity=Severity(ticket.severity),
        hazard_type=HazardType(ticket.hazard_type),
        location_on_board=ticket.location_on_board or "",
        created_at=ticket.created_at,
    )
    get_hub().publish_event(
        [master_channel(vessel_id)],
        SseEvent.TICKET_NEW,
        data.model_dump(mode="json"),
    )


def emit_ticket_updated(*, ticket: Ticket, vessel_id: str) -> None:
    data = TicketUpdatedData(
        ticket_id=ticket.id,
        ticket_no=ticket.ticket_no,
        onboard_status=OnboardStatus(ticket.onboard_status),
        shore_status=ShoreStatus(ticket.shore_status),
    )
    payload = data.model_dump(mode="json")
    channels = [master_channel(vessel_id), crew_channel(ticket.reporter_crew_id)]
    get_hub().publish_event(channels, SseEvent.TICKET_UPDATED, payload)


def emit_message_new(
    *,
    ticket: Ticket,
    message_id: str,
    sender: str,
    created_at: datetime,
    vessel_id: str,
) -> None:
    """Notify the other party only (no body text on the wire)."""
    data = {
        "message_id": message_id,
        "ticket_id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "sender": sender,
        "created_at": created_at.isoformat(),
    }
    if sender == "reporter":
        channels = [master_channel(vessel_id)]
    else:
        # master or shore → reporter
        channels = [crew_channel(ticket.reporter_crew_id)]
    get_hub().publish_event(channels, SseEvent.MESSAGE_NEW, data)


def emit_sync_status(data: dict, *, vessel_id: str) -> None:
    from beacon_contract.events import vessel_channel

    get_hub().publish_event(
        [master_channel(vessel_id), vessel_channel(vessel_id)],
        SseEvent.SYNC_STATUS,
        data,
    )
