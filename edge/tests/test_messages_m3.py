"""M3 — ticket messages, inbox, SSE message.new, reporter outbox."""

from __future__ import annotations

import asyncio
import json

import pytest
from beacon_contract import fixtures
from beacon_contract.edge_api import CrewTicket, InboxItem, MessageView, StructureResponse
from beacon_contract.enums import InboxKind, MessageSender, SseEvent, SyncEntity
from beacon_contract.events import crew_channel, master_channel
from beacon_contract.sync import TicketMessagePayload
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.pairing import create_pairing_code
from app.config import get_settings
from app.db.models import Outbox
from app.events.hub import get_hub


async def _submit_report(
    client: AsyncClient, headers: dict, *, key: str = "m3"
) -> CrewTicket:
    draft = await client.post(
        "/api/v1/reports/drafts",
        headers={**headers, "Idempotency-Key": f"{key}-d"},
        data={"text": fixtures.HINDI_REPORT, "language": "hi"},
    )
    assert draft.status_code == 200, draft.text
    draft_id = draft.json()["draft_id"]

    structured = await client.post(
        f"/api/v1/reports/drafts/{draft_id}/structure",
        headers={**headers, "Idempotency-Key": f"{key}-s"},
    )
    assert structured.status_code == 200, structured.text
    fields = StructureResponse.model_validate(structured.json()).fields

    answered = await client.post(
        f"/api/v1/reports/drafts/{draft_id}/answer",
        headers={**headers, "Idempotency-Key": f"{key}-a"},
        json={"answer": "Main deck crane 2"},
    )
    assert answered.status_code == 200, answered.text
    after = StructureResponse.model_validate(answered.json()).fields

    sub = await client.post(
        "/api/v1/reports",
        headers={**headers, "Idempotency-Key": f"{key}-r"},
        json={
            "draft_id": draft_id,
            "fields": {
                "title_en": after.title_en or fields.title_en,
                "description_en": after.description_en or fields.description_en,
                "location_on_board": after.location_on_board or "Deck",
                "hazard_type": (after.hazard_type or fields.hazard_type).value,
                "ism_category": (after.ism_category or fields.ism_category).value,
                "severity": int(after.severity or fields.severity or 3),
                "immediate_action": after.immediate_action,
                "occurred_at": None,
            },
            "share_name_with_master": False,
        },
    )
    assert sub.status_code == 200, sub.text
    return CrewTicket.model_validate(sub.json())


@pytest.mark.asyncio
async def test_crew_cannot_read_others_messages(
    client: AsyncClient,
    session: AsyncSession,
    paired_crew: dict,
    paired_master: dict,
):
    ticket = await _submit_report(client, paired_crew["headers"], key="own")
    await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_master["headers"],
        json={"body": "Please isolate the crane"},
    )

    plaintext, _ = await create_pairing_code(session, "c-0007-bos")
    await session.commit()
    pair = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": plaintext, "crew_id": "c-0007-bos", "pin": "1234"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"device_token": pair.json()["device_token"], "pin": "1234"},
    )
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}

    forbidden = await client.get(
        f"/api/v1/tickets/{ticket.ticket_id}/messages", headers=other
    )
    assert forbidden.status_code == 403

    post_forbidden = await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=other,
        json={"body": "not my ticket"},
    )
    assert post_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_message_round_trip_senders_and_inbox(
    client: AsyncClient, paired_crew: dict, paired_master: dict
):
    ticket = await _submit_report(client, paired_crew["headers"], key="rt")

    crew_msg = await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_crew["headers"],
        json={"body": "Oil is still leaking near Arun Yadav's station"},
    )
    assert crew_msg.status_code == 200, crew_msg.text
    view = MessageView.model_validate(crew_msg.json())
    assert view.sender == MessageSender.REPORTER
    assert "Arun Yadav" in view.body  # edge keeps original; scrub is outbox-only

    master_inbox = await client.get("/api/v1/inbox", headers=paired_master["headers"])
    assert master_inbox.status_code == 200
    items = [InboxItem.model_validate(i) for i in master_inbox.json()]
    assert any(i.ref_id == ticket.ticket_id for i in items)

    master_msg = await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_master["headers"],
        json={"body": "We will fit a drip tray this watch"},
    )
    assert master_msg.status_code == 200
    assert MessageView.model_validate(master_msg.json()).sender == MessageSender.MASTER

    crew_inbox = await client.get("/api/v1/inbox", headers=paired_crew["headers"])
    assert crew_inbox.status_code == 200
    crew_items = [InboxItem.model_validate(i) for i in crew_inbox.json()]
    assert any(i.kind == InboxKind.MASTER_REPLY for i in crew_items)
    target = next(i for i in crew_items if i.kind == InboxKind.MASTER_REPLY)

    marked = await client.post(
        f"/api/v1/inbox/{target.inbox_id}/read",
        headers=paired_crew["headers"],
    )
    assert marked.status_code == 200
    assert InboxItem.model_validate(marked.json()).read_at is not None

    after = await client.get("/api/v1/inbox", headers=paired_crew["headers"])
    assert all(i["inbox_id"] != target.inbox_id for i in after.json())

    thread = await client.get(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_crew["headers"],
    )
    assert thread.status_code == 200
    assert len(thread.json()) == 2


@pytest.mark.asyncio
async def test_message_new_sse_to_other_party(
    client: AsyncClient, paired_crew: dict, paired_master: dict
):
    get_hub().reset()
    ticket = await _submit_report(client, paired_crew["headers"], key="sse")
    vessel = get_settings().vessel_id

    master_q = get_hub().subscribe([master_channel(vessel)])
    crew_q = get_hub().subscribe([crew_channel(paired_crew["crew_id"])])

    await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_crew["headers"],
        json={"body": "Update from deck"},
    )
    master_ev = await asyncio.wait_for(master_q.get(), timeout=1.0)
    assert master_ev.event == SseEvent.MESSAGE_NEW
    assert master_ev.data["ticket_id"] == ticket.ticket_id
    assert master_ev.data["sender"] == "reporter"
    assert "body" not in master_ev.data

    # Crew should not get their own message on crew channel.
    try:
        await asyncio.wait_for(crew_q.get(), timeout=0.2)
        pytest.fail("reporter received own message.new")
    except TimeoutError:
        pass

    await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_master["headers"],
        json={"body": "Acknowledged on board"},
    )
    crew_ev = await asyncio.wait_for(crew_q.get(), timeout=1.0)
    assert crew_ev.event == SseEvent.MESSAGE_NEW
    assert crew_ev.data["sender"] == "master"


@pytest.mark.asyncio
async def test_reporter_message_outbox_scrubbed(
    client: AsyncClient,
    session: AsyncSession,
    paired_crew: dict,
    paired_master: dict,
):
    ticket = await _submit_report(client, paired_crew["headers"], key="ob")

    await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_crew["headers"],
        json={"body": "Please tell Arun Yadav the deck is clear"},
    )
    await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_master["headers"],
        json={"body": "Master note stays on edge"},
    )

    session.expire_all()
    rows = list(
        (
            await session.execute(
                select(Outbox).where(Outbox.entity == SyncEntity.TICKET_MESSAGE.value)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    payload = TicketMessagePayload.model_validate(rows[0].payload)
    assert payload.sender == "reporter"
    assert "Arun Yadav" not in payload.body
    assert "[crew]" in payload.body
    raw = json.dumps(rows[0].payload)
    assert "reporter_crew_id" not in raw
    assert "c-0007-aru" not in raw


@pytest.mark.asyncio
async def test_unread_messages_on_crew_ticket(
    client: AsyncClient, paired_crew: dict, paired_master: dict
):
    ticket = await _submit_report(client, paired_crew["headers"], key="unr")

    await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_master["headers"],
        json={"body": "First master note"},
    )
    await client.post(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_master["headers"],
        json={"body": "Second master note"},
    )

    mine = await client.get("/api/v1/reports/mine", headers=paired_crew["headers"])
    assert mine.status_code == 200
    item = next(t for t in mine.json() if t["ticket_id"] == ticket.ticket_id)
    assert CrewTicket.model_validate(item).unread_messages == 2

    # Opening the thread marks master messages read.
    opened = await client.get(
        f"/api/v1/tickets/{ticket.ticket_id}/messages",
        headers=paired_crew["headers"],
    )
    assert opened.status_code == 200

    mine2 = await client.get("/api/v1/reports/mine", headers=paired_crew["headers"])
    item2 = next(t for t in mine2.json() if t["ticket_id"] == ticket.ticket_id)
    assert CrewTicket.model_validate(item2).unread_messages == 0
