"""M4 — outbox push/pull against respx-mocked shore."""

from __future__ import annotations

import gzip
from datetime import UTC, datetime

import httpx
import pytest
import respx
from beacon_contract import fixtures, new_id, reporter_ref
from beacon_contract.edge_api import CrewTicket, StructureResponse, SyncStatus
from beacon_contract.enums import InboxKind, PullChangeType, ShoreStatus
from beacon_contract.security import (
    HEADER_SIGNATURE,
    HEADER_TIMESTAMP,
    verify_request,
)
from beacon_contract.sync import (
    PullChange,
    PullResponse,
    PushEventAck,
    PushResponse,
    ShoreMessageChange,
    SyncDelta,
    TicketShoreStatusChange,
)
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Inbox, Outbox, SyncState, Ticket
from app.sync.client import ShoreClient
from app.sync.cycle import reset_probe_streak, run_sync_cycle
from app.sync.state import get_or_create_sync_state


async def _submit_report(
    client: AsyncClient, headers: dict, *, key: str
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
        json={"answer": "Crane 2 starboard"},
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


def _shore_base() -> str:
    return get_settings().shore_url.rstrip("/")


def _signed_path(request: httpx.Request) -> str:
    path = request.url.path
    q = request.url.query
    if isinstance(q, (bytes, bytearray)):
        q = q.decode()
    return f"{path}?{q}" if q else path


@pytest.fixture(autouse=True)
def _shore_api_key(monkeypatch):
    monkeypatch.setenv("BEACON_SHORE_API_KEY", "demo-shore-api-key")
    get_settings.cache_clear()
    reset_probe_streak()
    yield
    get_settings.cache_clear()
    reset_probe_streak()


@pytest.mark.asyncio
@respx.mock
async def test_push_signature_valid(session: AsyncSession):
    settings = get_settings()
    captured: dict = {}

    def _push_handler(request: httpx.Request) -> httpx.Response:
        body = request.content
        captured["headers"] = dict(request.headers)
        captured["body"] = body
        assert verify_request(
            "demo-shore-api-key",
            "POST",
            _signed_path(request),
            int(request.headers[HEADER_TIMESTAMP]),
            body,
            request.headers[HEADER_SIGNATURE],
        )
        raw = gzip.decompress(body)
        delta = SyncDelta.model_validate_json(raw)
        return httpx.Response(
            200,
            json=PushResponse(
                batch_id=delta.batch_id,
                acks=[
                    PushEventAck(event_id=e.event_id, status="applied")
                    for e in delta.events
                ],
            ).model_dump(mode="json"),
        )

    respx.get(f"{_shore_base()}/api/v1/healthz").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    respx.post(f"{_shore_base()}/api/v1/sync/push").mock(side_effect=_push_handler)
    respx.get(url__regex=r".*/api/v1/sync/pull.*").mock(
        return_value=httpx.Response(
            200,
            json=PullResponse(changes=[], next_cursor="1", has_more=False).model_dump(
                mode="json"
            ),
        )
    )

    from app.services.outbox_tickets import enqueue_ticket_insert

    now = datetime.now(UTC)
    tid = new_id()
    ticket = Ticket(
        id=tid,
        ticket_no="BCN-0007-9001",
        vessel_id=settings.vessel_id,
        reporter_ref=reporter_ref(settings.vessel_secret, "c-0007-aru", tid),
        reporter_crew_id="c-0007-aru",
        rank_band="rating",
        title_en="Test",
        description_en="Desc",
        original_language="en",
        location_on_board="Deck",
        hazard_type="slip_trip_fall",
        ism_category="unsafe_condition",
        severity=3,
        onboard_status="NEW",
        shore_status="QUEUED_FOR_LINK",
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    await session.flush()
    await enqueue_ticket_insert(session, ticket=ticket)
    state = await get_or_create_sync_state(session, settings=settings)
    state.link_override = "up"
    await session.commit()

    reset_probe_streak()
    http = httpx.AsyncClient(base_url=_shore_base())
    client = ShoreClient(settings, client=http)
    summary = await run_sync_cycle(
        session, settings=settings, client=client, force_probe=True
    )
    await http.aclose()

    assert summary.get("pushed_bytes", 0) > 0
    assert any(k.lower() == "x-signature" for k in captured["headers"])
    assert captured["body"][:2] == b"\x1f\x8b"


@pytest.mark.asyncio
@respx.mock
async def test_duplicate_acks(session: AsyncSession):
    settings = get_settings()
    seen: set[str] = set()

    def _push_handler(request: httpx.Request) -> httpx.Response:
        raw = gzip.decompress(request.content)
        delta = SyncDelta.model_validate_json(raw)
        acks = []
        for e in delta.events:
            if e.event_id in seen:
                acks.append(PushEventAck(event_id=e.event_id, status="duplicate"))
            else:
                seen.add(e.event_id)
                acks.append(PushEventAck(event_id=e.event_id, status="applied"))
        return httpx.Response(
            200,
            json=PushResponse(batch_id=delta.batch_id, acks=acks).model_dump(mode="json"),
        )

    respx.get(f"{_shore_base()}/api/v1/healthz").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    respx.post(f"{_shore_base()}/api/v1/sync/push").mock(side_effect=_push_handler)
    respx.get(url__regex=r".*/api/v1/sync/pull.*").mock(
        return_value=httpx.Response(
            200,
            json=PullResponse(changes=[], next_cursor="0", has_more=False).model_dump(
                mode="json"
            ),
        )
    )

    from app.services.outbox_tickets import enqueue_ticket_insert

    now = datetime.now(UTC)
    tid = new_id()
    ticket = Ticket(
        id=tid,
        ticket_no="BCN-0007-9002",
        vessel_id=settings.vessel_id,
        reporter_ref=reporter_ref(settings.vessel_secret, "c-0007-aru", tid),
        reporter_crew_id="c-0007-aru",
        rank_band="rating",
        title_en="Dup",
        description_en="Desc",
        original_language="en",
        location_on_board="Deck",
        hazard_type="slip_trip_fall",
        ism_category="unsafe_condition",
        severity=5,
        onboard_status="NEW",
        shore_status="QUEUED_FOR_LINK",
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    await session.flush()
    await enqueue_ticket_insert(session, ticket=ticket)
    state = await get_or_create_sync_state(session, settings=settings)
    state.link_override = "up"
    await session.commit()

    event_id = (
        await session.execute(select(Outbox).where(Outbox.entity_id == tid))
    ).scalar_one().id

    http = httpx.AsyncClient(base_url=_shore_base())
    client = ShoreClient(settings, client=http)
    await run_sync_cycle(session, settings=settings, client=client, force_probe=True)
    # Re-queue same event id as unpushed to simulate retry
    row = await session.get(Outbox, event_id)
    assert row is not None
    row.pushed_at = None
    await session.commit()

    await run_sync_cycle(session, settings=settings, client=client, force_probe=True)
    await http.aclose()

    row = await session.get(Outbox, event_id)
    assert row is not None and row.pushed_at is not None
    assert event_id in seen


@pytest.mark.asyncio
@respx.mock
async def test_override_down_sends_nothing(
    client: AsyncClient, session: AsyncSession, paired_crew: dict, paired_master: dict
):
    await _submit_report(client, paired_crew["headers"], key="down1")
    await _submit_report(client, paired_crew["headers"], key="down2")

    ov = await client.post(
        "/api/v1/sync/override",
        headers=paired_master["headers"],
        json={"mode": "down"},
    )
    assert ov.status_code == 200, ov.text
    assert SyncStatus.model_validate(ov.json()).link.value == "DOWN"

    push_route = respx.post(f"{_shore_base()}/api/v1/sync/push").mock(
        return_value=httpx.Response(500)
    )
    respx.get(f"{_shore_base()}/api/v1/healthz").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    now = await client.post("/api/v1/sync/now", headers=paired_master["headers"])
    assert now.status_code == 200, now.text
    status = SyncStatus.model_validate(now.json())
    assert status.link.value == "DOWN"
    assert status.pending_events >= 2
    assert not push_route.called

    st = await client.get("/api/v1/sync/status", headers=paired_master["headers"])
    assert SyncStatus.model_validate(st.json()).pending_events >= 2


@pytest.mark.asyncio
@respx.mock
async def test_pull_shore_reply_inbox_and_cursor(
    client: AsyncClient, session: AsyncSession, paired_crew: dict, paired_master: dict
):
    ticket = await _submit_report(client, paired_crew["headers"], key="pull1")
    settings = get_settings()
    ref = reporter_ref(settings.vessel_secret, paired_crew["crew_id"], ticket.ticket_id)

    pull_calls = {"n": 0}

    def _pull_handler(request: httpx.Request) -> httpx.Response:
        pull_calls["n"] += 1
        # Verify signature
        assert verify_request(
            "demo-shore-api-key",
            "GET",
            _signed_path(request),
            int(request.headers[HEADER_TIMESTAMP]),
            b"",
            request.headers[HEADER_SIGNATURE],
        )
        if pull_calls["n"] == 1:
            now = datetime.now(UTC)
            body = PullResponse(
                changes=[
                    PullChange(
                        change_id=new_id(),
                        type=PullChangeType.TICKET_SHORE_STATUS,
                        created_at=now,
                        payload=TicketShoreStatusChange(
                            ticket_id=ticket.ticket_id,
                            shore_status=ShoreStatus.IN_REVIEW,
                            updated_at=now,
                        ).model_dump(mode="json"),
                    ),
                    PullChange(
                        change_id=new_id(),
                        type=PullChangeType.TICKET_MESSAGE,
                        created_at=now,
                        payload=ShoreMessageChange(
                            message_id=new_id(),
                            ticket_id=ticket.ticket_id,
                            reporter_ref=ref,
                            body="Thank you. Was the leak source found?",
                            created_at=now,
                        ).model_dump(mode="json"),
                    ),
                ],
                next_cursor="cursor-1",
                has_more=False,
            )
            return httpx.Response(200, json=body.model_dump(mode="json"))
        return httpx.Response(
            200,
            json=PullResponse(
                changes=[], next_cursor="cursor-1", has_more=False
            ).model_dump(mode="json"),
        )

    def _push_handler(request: httpx.Request) -> httpx.Response:
        raw = gzip.decompress(request.content)
        delta = SyncDelta.model_validate_json(raw)
        return httpx.Response(
            200,
            json=PushResponse(
                batch_id=delta.batch_id,
                acks=[
                    PushEventAck(event_id=e.event_id, status="applied")
                    for e in delta.events
                ],
            ).model_dump(mode="json"),
        )

    respx.get(f"{_shore_base()}/api/v1/healthz").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    respx.post(f"{_shore_base()}/api/v1/sync/push").mock(side_effect=_push_handler)
    respx.get(url__regex=r".*/api/v1/sync/pull.*").mock(side_effect=_pull_handler)

    await client.post(
        "/api/v1/sync/override",
        headers=paired_master["headers"],
        json={"mode": "up"},
    )
    reset_probe_streak()
    r = await client.post("/api/v1/sync/now", headers=paired_master["headers"])
    assert r.status_code == 200, r.text
    status = SyncStatus.model_validate(r.json())
    assert status.last_push_bytes_gz is not None and status.last_push_bytes_gz > 0
    assert status.last_pull_at is not None

    session.expire_all()
    sync_row = await session.get(SyncState, settings.vessel_id)
    assert sync_row is not None
    assert sync_row.last_pull_cursor == "cursor-1"

    inbox = list(
        (
            await session.execute(
                select(Inbox).where(
                    Inbox.crew_id == paired_crew["crew_id"],
                    Inbox.kind == InboxKind.SHORE_REPLY.value,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(inbox) >= 1

    db_ticket = await session.get(Ticket, ticket.ticket_id)
    assert db_ticket is not None
    assert db_ticket.shore_status == ShoreStatus.IN_REVIEW.value

    # Second sync: cursor stays advanced; pull still called with cursor-1
    await client.post("/api/v1/sync/now", headers=paired_master["headers"])
    assert pull_calls["n"] >= 2
