"""Master board: list, ack, actions (M2)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from beacon_contract import new_id
from beacon_contract.edge_api import LearningStatsView, MasterTicket, TicketActionCreate
from beacon_contract.enums import ActionType, ActorRole, InboxKind, OnboardStatus
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, require_role
from app.db.models import Inbox, Ticket, TicketAction
from app.db.session import get_session
from app.errors import AppError
from app.events.emit import emit_ticket_updated
from app.services.learnings import list_learning_stats
from app.services.master_tickets import get_master_ticket, list_master_tickets
from app.services.outbox_tickets import enqueue_ticket_action, enqueue_ticket_upsert

router = APIRouter(prefix="/master", tags=["master"])


def _inbox_status(session: AsyncSession, *, crew_id: str, ticket_id: str, title: str) -> None:
    now = datetime.now(UTC)
    session.add(
        Inbox(
            id=new_id(),
            crew_id=crew_id,
            kind=InboxKind.STATUS_CHANGE.value,
            ref_id=ticket_id,
            title=title,
            created_at=now,
        )
    )


@router.get("/learnings/stats", response_model=list[LearningStatsView])
async def master_learning_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
) -> list[LearningStatsView]:
    return await list_learning_stats(session)


@router.get("/tickets", response_model=list[MasterTicket])
async def master_tickets(
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
    onboard_status: str | None = None,
    severity: int | None = None,
) -> list[MasterTicket]:
    return await list_master_tickets(
        session, onboard_status=onboard_status, severity=severity
    )


@router.post("/tickets/{ticket_id}/ack", response_model=MasterTicket)
async def ack_ticket(
    ticket_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
) -> MasterTicket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise AppError("not_found", "Ticket not found", status_code=404)

    now = datetime.now(UTC)
    action = TicketAction(
        id=new_id(),
        ticket_id=ticket.id,
        actor_role=ActorRole.MASTER.value,
        action_type=ActionType.ACK.value,
        text=None,
        created_at=now,
        updated_at=now,
        origin="edge",
        version=1,
    )
    session.add(action)
    ticket.onboard_status = OnboardStatus.ACKNOWLEDGED.value
    ticket.updated_at = now

    await session.flush()
    await enqueue_ticket_action(session, action=action)
    await enqueue_ticket_upsert(session, ticket=ticket)
    _inbox_status(
        session,
        crew_id=ticket.reporter_crew_id,
        ticket_id=ticket.id,
        title=f"Master acknowledged {ticket.ticket_no}",
    )
    await session.commit()

    emit_ticket_updated(ticket=ticket, vessel_id=principal.vessel_id)

    view = await get_master_ticket(session, ticket.id)
    assert view is not None
    return view


@router.post("/tickets/{ticket_id}/actions", response_model=MasterTicket)
async def add_action(
    ticket_id: str,
    body: TicketActionCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
) -> MasterTicket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise AppError("not_found", "Ticket not found", status_code=404)

    now = datetime.now(UTC)
    if body.resolve:
        action_type = ActionType.RESOLVE
        status = OnboardStatus.RESOLVED_ON_BOARD
        inbox_title = f"Master resolved {ticket.ticket_no}"
    else:
        action_type = ActionType.ACTION
        status = OnboardStatus.ACTION_IN_PROGRESS
        inbox_title = f"Master updated {ticket.ticket_no}"

    action = TicketAction(
        id=new_id(),
        ticket_id=ticket.id,
        actor_role=ActorRole.MASTER.value,
        action_type=action_type.value,
        text=body.text,
        responsible_rank=body.responsible_rank,
        due_at=body.due_at,
        created_at=now,
        updated_at=now,
        origin="edge",
        version=1,
    )
    session.add(action)
    ticket.onboard_status = status.value
    ticket.updated_at = now

    await session.flush()
    await enqueue_ticket_action(session, action=action)
    await enqueue_ticket_upsert(session, ticket=ticket)
    _inbox_status(
        session,
        crew_id=ticket.reporter_crew_id,
        ticket_id=ticket.id,
        title=inbox_title,
    )
    await session.commit()

    emit_ticket_updated(ticket=ticket, vessel_id=principal.vessel_id)

    view = await get_master_ticket(session, ticket.id)
    assert view is not None
    return view
