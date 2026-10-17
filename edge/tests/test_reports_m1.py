"""M1 reports flow — FakeAIGateway, privacy, outbox, idempotency, rails."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from beacon_contract import fixtures
from beacon_contract.edge_api import CrewTicket, DraftCreated, StructureResponse
from beacon_contract.enums import SyncEntity, SyncOp
from beacon_contract.sync import SyncEvent
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.pairing import create_pairing_code
from app.db.models import Draft, Outbox, Ticket
from app.services.media import media_root


def _tiny_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(40, 80, 120)).save(buf, format="JPEG")
    return buf.getvalue()


async def _pair_crew(client: AsyncClient, session: AsyncSession, crew_id: str, pin: str) -> dict:
    # Need a master session to create codes — use create_pairing_code directly.
    plaintext, _ = await create_pairing_code(session, crew_id)
    await session.commit()
    pair = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": plaintext, "crew_id": crew_id, "pin": pin},
    )
    assert pair.status_code == 200, pair.text
    device_token = pair.json()["device_token"]
    login = await client.post(
        "/api/v1/auth/login",
        json={"device_token": device_token, "pin": pin},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {
        "crew_id": crew_id,
        "headers": {"Authorization": f"Bearer {token}"},
        "device_token": device_token,
    }


@pytest.mark.asyncio
async def test_reports_full_flow_fake_gateway(client: AsyncClient, paired_crew: dict):
    headers = {**paired_crew["headers"], "Idempotency-Key": "draft-1"}
    r = await client.post(
        "/api/v1/reports/drafts",
        headers=headers,
        data={"text": fixtures.HINDI_REPORT, "language": "hi"},
        files=[("photos", ("deck.jpg", _tiny_jpeg(), "image/jpeg"))],
    )
    assert r.status_code == 200, r.text
    created = DraftCreated.model_validate(r.json())
    assert created.draft_id
    assert len(created.media) == 1

    s = await client.post(
        f"/api/v1/reports/drafts/{created.draft_id}/structure",
        headers={**paired_crew["headers"], "Idempotency-Key": "struct-1"},
    )
    assert s.status_code == 200, s.text
    structured = StructureResponse.model_validate(s.json())
    assert structured.safety.rail_hit is False
    assert structured.fields.hazard_type is not None
    assert structured.clarifying_question is not None

    a = await client.post(
        f"/api/v1/reports/drafts/{created.draft_id}/answer",
        headers={**paired_crew["headers"], "Idempotency-Key": "ans-1"},
        json={"answer": "Main deck, crane no. 2, starboard"},
    )
    assert a.status_code == 200, a.text
    after = StructureResponse.model_validate(a.json())
    assert after.fields.location_on_board
    assert after.clarifying_question is None

    submit_body = {
        "draft_id": created.draft_id,
        "fields": {
            "title_en": after.fields.title_en,
            "description_en": after.fields.description_en,
            "location_on_board": after.fields.location_on_board,
            "hazard_type": after.fields.hazard_type.value,
            "ism_category": after.fields.ism_category.value,
            "severity": int(after.fields.severity),
            "immediate_action": after.fields.immediate_action,
            "occurred_at": None,
        },
        "share_name_with_master": False,
    }
    sub = await client.post(
        "/api/v1/reports",
        headers={**paired_crew["headers"], "Idempotency-Key": "sub-1"},
        json=submit_body,
    )
    assert sub.status_code == 200, sub.text
    ticket = CrewTicket.model_validate(sub.json())
    assert ticket.ticket_no.startswith("BCN-0007-")
    assert ticket.onboard_status == "NEW"
    assert ticket.shore_status == "QUEUED_FOR_LINK"

    mine = await client.get("/api/v1/reports/mine", headers=paired_crew["headers"])
    assert mine.status_code == 200
    assert any(t["ticket_id"] == ticket.ticket_id for t in mine.json())


@pytest.mark.asyncio
async def test_crew_cannot_see_others_tickets(
    client: AsyncClient, session: AsyncSession, paired_crew: dict
):
    # Submit one ticket as aru
    draft = await client.post(
        "/api/v1/reports/drafts",
        headers=paired_crew["headers"],
        data={"text": "oil on deck near crane", "language": "en"},
    )
    draft_id = draft.json()["draft_id"]
    await client.post(
        f"/api/v1/reports/drafts/{draft_id}/structure",
        headers=paired_crew["headers"],
    )
    after = fixtures.structure_after_answer()
    sub = await client.post(
        "/api/v1/reports",
        headers=paired_crew["headers"],
        json={
            "draft_id": draft_id,
            "fields": {
                "title_en": after.fields.title_en,
                "description_en": after.fields.description_en,
                "location_on_board": after.fields.location_on_board,
                "hazard_type": after.fields.hazard_type.value,
                "ism_category": after.fields.ism_category.value,
                "severity": int(after.fields.severity),
            },
            "share_name_with_master": False,
        },
    )
    assert sub.status_code == 200
    aru_ticket_id = sub.json()["ticket_id"]

    other = await _pair_crew(client, session, "c-0007-ab2", "1234")
    mine = await client.get("/api/v1/reports/mine", headers=other["headers"])
    assert mine.status_code == 200
    assert all(t["ticket_id"] != aru_ticket_id for t in mine.json())


@pytest.mark.asyncio
async def test_outbox_sync_event_no_roster_name_or_crew_id(
    client: AsyncClient, session: AsyncSession, paired_crew: dict
):
    draft = await client.post(
        "/api/v1/reports/drafts",
        headers=paired_crew["headers"],
        data={"text": "Arun Yadav slipped near Capt. Rajiv Menon at crane", "language": "en"},
    )
    draft_id = draft.json()["draft_id"]
    await client.post(
        f"/api/v1/reports/drafts/{draft_id}/structure",
        headers=paired_crew["headers"],
    )
    after = fixtures.structure_after_answer()
    # Force a title/description that includes roster names so scrub must run.
    sub = await client.post(
        "/api/v1/reports",
        headers=paired_crew["headers"],
        json={
            "draft_id": draft_id,
            "fields": {
                "title_en": "Arun Yadav slip by Capt. Rajiv Menon",
                "description_en": "Arun Yadav nearly fell; Capt. Rajiv Menon was nearby.",
                "location_on_board": after.fields.location_on_board,
                "hazard_type": after.fields.hazard_type.value,
                "ism_category": after.fields.ism_category.value,
                "severity": int(after.fields.severity),
            },
            "share_name_with_master": False,
        },
    )
    assert sub.status_code == 200, sub.text
    ticket_id = sub.json()["ticket_id"]

    row = (
        await session.execute(select(Outbox).where(Outbox.entity_id == ticket_id))
    ).scalar_one()
    event = SyncEvent(
        event_id=row.id,
        entity=SyncEntity(row.entity),
        op=SyncOp(row.op),
        entity_id=row.entity_id,
        version=row.version,
        occurred_at=row.created_at,
        owned_fields=row.payload,
        payload=None,
    )
    # Validates (raises if forbidden keys / bad shape).
    SyncEvent.model_validate(event.model_dump())
    blob = str(row.payload)
    assert "crew_id" not in row.payload
    assert "reporter_crew_id" not in row.payload
    assert "Arun" not in blob
    assert "Rajiv" not in blob
    assert "Yadav" not in blob
    assert "Menon" not in blob
    assert row.payload["reporter_ref"].startswith("rr_")


@pytest.mark.asyncio
async def test_audio_deleted_after_submit(
    client: AsyncClient, session: AsyncSession, paired_crew: dict
):
    audio_bytes = b"fake-webm-bytes"
    r = await client.post(
        "/api/v1/reports/drafts",
        headers=paired_crew["headers"],
        data={"language": "hi"},
        files=[("audio", ("clip.webm", audio_bytes, "audio/webm"))],
    )
    assert r.status_code == 200, r.text
    draft_id = r.json()["draft_id"]
    draft = await session.get(Draft, draft_id)
    assert draft is not None and draft.audio_path
    audio_path = Path(draft.audio_path)
    assert audio_path.is_file()

    await client.post(
        f"/api/v1/reports/drafts/{draft_id}/structure",
        headers=paired_crew["headers"],
    )
    after = fixtures.structure_after_answer()
    sub = await client.post(
        "/api/v1/reports",
        headers=paired_crew["headers"],
        json={
            "draft_id": draft_id,
            "fields": {
                "title_en": after.fields.title_en,
                "description_en": after.fields.description_en,
                "location_on_board": after.fields.location_on_board or "deck",
                "hazard_type": after.fields.hazard_type.value,
                "ism_category": after.fields.ism_category.value,
                "severity": int(after.fields.severity),
            },
        },
    )
    assert sub.status_code == 200, sub.text
    assert not audio_path.exists()
    await session.refresh(draft)
    assert draft.audio_path is None


@pytest.mark.asyncio
async def test_idempotent_submit_same_ticket(client: AsyncClient, paired_crew: dict):
    draft = await client.post(
        "/api/v1/reports/drafts",
        headers=paired_crew["headers"],
        data={"text": "hydraulic leak", "language": "en"},
    )
    draft_id = draft.json()["draft_id"]
    await client.post(
        f"/api/v1/reports/drafts/{draft_id}/structure",
        headers=paired_crew["headers"],
    )
    after = fixtures.structure_after_answer()
    payload = {
        "draft_id": draft_id,
        "fields": {
            "title_en": after.fields.title_en,
            "description_en": after.fields.description_en,
            "location_on_board": after.fields.location_on_board or "deck",
            "hazard_type": after.fields.hazard_type.value,
            "ism_category": after.fields.ism_category.value,
            "severity": int(after.fields.severity),
        },
    }
    headers = {**paired_crew["headers"], "Idempotency-Key": "same-submit-key"}
    a = await client.post("/api/v1/reports", headers=headers, json=payload)
    b = await client.post("/api/v1/reports", headers=headers, json=payload)
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["ticket_id"] == b.json()["ticket_id"]
    assert a.json()["ticket_no"] == b.json()["ticket_no"]


@pytest.mark.asyncio
async def test_rail_hit_never_calls_gateway(client: AsyncClient, paired_crew: dict):
    draft = await client.post(
        "/api/v1/reports/drafts",
        headers=paired_crew["headers"],
        data={"text": "I want to die", "language": "en"},
    )
    draft_id = draft.json()["draft_id"]

    mock_gw = AsyncMock()
    with patch("app.api.reports.get_gateway", return_value=mock_gw):
        r = await client.post(
            f"/api/v1/reports/drafts/{draft_id}/structure",
            headers=paired_crew["headers"],
        )
    assert r.status_code == 200, r.text
    body = StructureResponse.model_validate(r.json())
    assert body.safety.rail_hit is True
    assert body.safety.fixed_message
    mock_gw.structure_report.assert_not_called()
    mock_gw.transcribe.assert_not_called()
    mock_gw.caption_photos.assert_not_called()
