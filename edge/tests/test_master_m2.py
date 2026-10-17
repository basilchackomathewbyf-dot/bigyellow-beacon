"""M2 — Master board, ack/actions, SSE hub."""

from __future__ import annotations

import asyncio

import pytest
from beacon_contract import fixtures, new_id
from beacon_contract.edge_api import CrewTicket, MasterTicket, StructureResponse
from beacon_contract.enums import OnboardStatus, SseEvent, SyncEntity
from beacon_contract.events import crew_channel, master_channel
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.pairing import create_pairing_code
from app.config import get_settings
from app.db.models import Inbox, Outbox, Ticket
from app.events.hub import get_hub


async def _submit_report(
    client: AsyncClient, headers: dict, *, share_name: bool = False, key: str = "sub"
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
        json={"answer": "Main deck crane 2 starboard"},
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
                "location_on_board": after.location_on_board or "Deck crane",
                "hazard_type": (after.hazard_type or fields.hazard_type).value,
                "ism_category": (after.ism_category or fields.ism_category).value,
                "severity": int(after.severity or fields.severity or 3),
                "immediate_action": after.immediate_action,
                "occurred_at": None,
            },
            "share_name_with_master": share_name,
        },
    )
    assert sub.status_code == 200, sub.text
    return CrewTicket.model_validate(sub.json())


@pytest.mark.asyncio
async def test_ticket_new_arrives_within_1s(
    client: AsyncClient, paired_crew: dict
):
    """Master channel receives ticket.new within 1s of submit."""
    get_hub().reset()
    vessel = get_settings().vessel_id
    q = get_hub().subscribe([master_channel(vessel)])

    ticket = await _submit_report(client, paired_crew["headers"], key="sse1")
    msg = await asyncio.wait_for(q.get(), timeout=1.0)
    assert msg is not None
    assert msg.event == SseEvent.TICKET_NEW
    assert msg.data["ticket_id"] == ticket.ticket_id
    # Wire format used by GET /events
    encoded = msg.encode()
    assert f"event: {SseEvent.TICKET_NEW.value}" in encoded
    assert f"id: {msg.id}" in encoded


@pytest.mark.asyncio
async def test_crew_stream_does_not_get_other_crew_events(
    client: AsyncClient,
    session: AsyncSession,
    paired_master: dict,
    paired_crew: dict,
):
    get_hub().reset()
    plaintext, _ = await create_pairing_code(session, "c-0007-bos")
    await session.commit()
    pair = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": plaintext, "crew_id": "c-0007-bos", "pin": "1234"},
    )
    assert pair.status_code == 200, pair.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"device_token": pair.json()["device_token"], "pin": "1234"},
    )
    assert login.status_code == 200
    other_id = "c-0007-bos"

    ticket = await _submit_report(client, paired_crew["headers"], key="iso")
    ack = await client.post(
        f"/api/v1/master/tickets/{ticket.ticket_id}/ack",
        headers=paired_master["headers"],
    )
    assert ack.status_code == 200, ack.text

    other_replay = get_hub().replay_since([crew_channel(other_id)], None)
    assert not any(
        m.event in (SseEvent.TICKET_NEW, SseEvent.TICKET_UPDATED)
        and m.data.get("ticket_id") == ticket.ticket_id
        for m in other_replay
    ), other_replay

    reporter_replay = get_hub().replay_since([crew_channel(paired_crew["crew_id"])], None)
    assert any(
        m.event == SseEvent.TICKET_UPDATED and m.data.get("ticket_id") == ticket.ticket_id
        for m in reporter_replay
    )

    master_replay = get_hub().replay_since(
        [master_channel(get_settings().vessel_id)], None
    )
    assert any(m.event == SseEvent.TICKET_NEW for m in master_replay)
    assert any(m.event == SseEvent.TICKET_UPDATED for m in master_replay)


@pytest.mark.asyncio
async def test_last_event_id_replay():
    get_hub().reset()
    ch = master_channel(get_settings().vessel_id)
    hub = get_hub()
    first = hub.publish_event([ch], SseEvent.TICKET_NEW, {"ticket_id": new_id(), "n": 1})
    second = hub.publish_event([ch], SseEvent.TICKET_NEW, {"ticket_id": new_id(), "n": 2})

    assert [m.id for m in hub.replay_since([ch], first.id)] == [second.id]
    assert [m.id for m in hub.replay_since([ch], None)] == [first.id, second.id]


@pytest.mark.asyncio
async def test_crew_403_on_master_ack_and_actions(
    client: AsyncClient, paired_crew: dict, paired_master: dict
):
    ticket = await _submit_report(client, paired_crew["headers"], key="f403")
    forbidden = await client.post(
        f"/api/v1/master/tickets/{ticket.ticket_id}/ack",
        headers=paired_crew["headers"],
    )
    assert forbidden.status_code == 403

    forbidden_act = await client.post(
        f"/api/v1/master/tickets/{ticket.ticket_id}/actions",
        headers=paired_crew["headers"],
        json={"text": "Isolate crane", "resolve": False},
    )
    assert forbidden_act.status_code == 403

    ok = await client.post(
        f"/api/v1/master/tickets/{ticket.ticket_id}/ack",
        headers=paired_master["headers"],
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_reporter_name_hidden_unless_opted_in(
    client: AsyncClient, paired_crew: dict, paired_master: dict
):
    hidden = await _submit_report(
        client, paired_crew["headers"], share_name=False, key="hide"
    )
    shown = await _submit_report(
        client, paired_crew["headers"], share_name=True, key="show"
    )

    listing = await client.get("/api/v1/master/tickets", headers=paired_master["headers"])
    assert listing.status_code == 200
    by_id = {t["ticket_id"]: MasterTicket.model_validate(t) for t in listing.json()}
    assert by_id[hidden.ticket_id].reporter_name is None
    assert by_id[shown.ticket_id].reporter_name is not None
    assert "c-0007-aru" not in listing.text


@pytest.mark.asyncio
async def test_ack_actions_outbox_and_inbox(
    client: AsyncClient,
    session: AsyncSession,
    paired_crew: dict,
    paired_master: dict,
):
    ticket = await _submit_report(client, paired_crew["headers"], key="act")

    ack = await client.post(
        f"/api/v1/master/tickets/{ticket.ticket_id}/ack",
        headers=paired_master["headers"],
    )
    assert ack.status_code == 200, ack.text
    view = MasterTicket.model_validate(ack.json())
    assert view.onboard_status == OnboardStatus.ACKNOWLEDGED
    assert any(a.action_type.value == "ack" for a in view.actions)

    act = await client.post(
        f"/api/v1/master/tickets/{ticket.ticket_id}/actions",
        headers=paired_master["headers"],
        json={"text": "Clean oil and fit drip tray", "resolve": False},
    )
    assert act.status_code == 200, act.text
    assert MasterTicket.model_validate(act.json()).onboard_status == (
        OnboardStatus.ACTION_IN_PROGRESS
    )

    done = await client.post(
        f"/api/v1/master/tickets/{ticket.ticket_id}/actions",
        headers=paired_master["headers"],
        json={"text": "Hazard cleared", "resolve": True},
    )
    assert done.status_code == 200, done.text
    assert MasterTicket.model_validate(done.json()).onboard_status == (
        OnboardStatus.RESOLVED_ON_BOARD
    )

    session.expire_all()
    outbox = list((await session.execute(select(Outbox))).scalars().all())
    entities = {row.entity for row in outbox}
    assert SyncEntity.TICKET.value in entities
    assert SyncEntity.TICKET_ACTION.value in entities

    inbox = list(
        (
            await session.execute(
                select(Inbox).where(Inbox.crew_id == paired_crew["crew_id"])
            )
        )
        .scalars()
        .all()
    )
    assert len(inbox) >= 3
    assert all(i.kind == "status_change" for i in inbox)

    db_ticket = await session.get(Ticket, ticket.ticket_id)
    assert db_ticket is not None
    assert db_ticket.onboard_status == OnboardStatus.RESOLVED_ON_BOARD.value


@pytest.mark.asyncio
async def test_events_accepts_access_token_query(
    client: AsyncClient, paired_master: dict, session: AsyncSession
):
    """Auth accepts ?access_token= (EventSource fallback); missing token → 401."""
    from starlette.requests import Request

    from app.auth.deps import resolve_principal

    no_auth = await client.get("/api/v1/events")
    assert no_auth.status_code == 401

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/events",
        "raw_path": b"/api/v1/events",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    request = Request(scope)
    principal = await resolve_principal(
        request, session, access_token=paired_master["access_token"]
    )
    assert principal.role == "master"
    assert principal.crew_id == paired_master["crew_id"]
