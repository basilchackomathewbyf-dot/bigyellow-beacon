"""Ticket message threads — GET/POST /tickets/{id}/messages (M3)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from beacon_contract import new_id
from beacon_contract.edge_api import MessageCreate, MessageView
from beacon_contract.enums import InboxKind, MessageSender
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, get_current_user
from app.config import get_settings
from app.db.models import Crew, Inbox, Ticket, TicketMessage
from app.db.session import get_session
from app.errors import AppError
from app.events.emit import emit_message_new
from app.services.outbox_tickets import enqueue_ticket_message

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _view(msg: TicketMessage) -> MessageView:
    return MessageView(
        message_id=msg.id,
        ticket_id=msg.ticket_id,
        sender=MessageSender(msg.sender),
        body=msg.body,
        created_at=msg.created_at,
        read_at=msg.read_at,
    )


async def _load_ticket_for_principal(
    session: AsyncSession, ticket_id: str, principal: AuthPrincipal
) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise AppError("not_found", "Ticket not found", status_code=404)
    if principal.role != "master" and ticket.reporter_crew_id != principal.crew_id:
        raise AppError("forbidden", "Not your ticket", status_code=403)
    return ticket


async def _mark_counterpart_read(
    session: AsyncSession,
    *,
    ticket_id: str,
    principal: AuthPrincipal,
) -> None:
    """Mark messages from the other party as read when the thread is opened."""
    now = datetime.now(UTC)
    if principal.role == "master":
        senders = (MessageSender.REPORTER.value,)
    else:
        senders = (MessageSender.MASTER.value, MessageSender.SHORE.value)
    rows = (
        await session.execute(
            select(TicketMessage).where(
                TicketMessage.ticket_id == ticket_id,
                TicketMessage.sender.in_(senders),
                TicketMessage.read_at.is_(None),
            )
        )
    ).scalars().all()
    for row in rows:
        row.read_at = now


@router.get("/{ticket_id}/messages", response_model=list[MessageView])
async def list_messages(
    ticket_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> list[MessageView]:
    await _load_ticket_for_principal(session, ticket_id, principal)
    await _mark_counterpart_read(session, ticket_id=ticket_id, principal=principal)
    await session.commit()

    rows = (
        await session.execute(
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.created_at.asc())
        )
    ).scalars().all()
    return [_view(m) for m in rows]


@router.post("/{ticket_id}/messages", response_model=MessageView)
async def post_message(
    ticket_id: str,
    body: MessageCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> MessageView:
    ticket = await _load_ticket_for_principal(session, ticket_id, principal)
    settings = get_settings()
    now = datetime.now(UTC)

    if principal.role == "master":
        sender = MessageSender.MASTER
    else:
        sender = MessageSender.REPORTER

    msg = TicketMessage(
        id=new_id(),
        ticket_id=ticket.id,
        sender=sender.value,
        body=body.body,
        created_at=now,
        updated_at=now,
        origin="edge",
        version=1,
    )
    session.add(msg)
    await session.flush()

    # Inbox for the other party + SSE.
    if sender == MessageSender.MASTER:
        session.add(
            Inbox(
                id=new_id(),
                crew_id=ticket.reporter_crew_id,
                kind=InboxKind.MASTER_REPLY.value,
                ref_id=ticket.id,
                title=f"Master replied on {ticket.ticket_no}",
                created_at=now,
            )
        )
        # Reporter-bound messages stay on the edge until shore pull; no outbox.
    else:
        # # DECISION: notify every active master on the vessel (inbox is per crew_id).
        masters = (
            await session.execute(
                select(Crew).where(
                    Crew.vessel_id == ticket.vessel_id,
                    Crew.is_master.is_(True),
                    Crew.active.is_(True),
                )
            )
        ).scalars().all()
        for master in masters:
            session.add(
                Inbox(
                    id=new_id(),
                    crew_id=master.id,
                    kind=InboxKind.STATUS_CHANGE.value,
                    ref_id=ticket.id,
                    title=f"Crew reply on {ticket.ticket_no}",
                    created_at=now,
                )
            )
        # Reporter → shore: scrubbed TicketMessagePayload outbox row.
        await enqueue_ticket_message(session, message=msg, vessel_id=ticket.vessel_id)

    await session.commit()

    emit_message_new(
        ticket=ticket,
        message_id=msg.id,
        sender=sender.value,
        created_at=now,
        vessel_id=settings.vessel_id,
    )
    return _view(msg)
