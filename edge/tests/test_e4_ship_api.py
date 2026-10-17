"""E4 Ship API — happy paths + required privacy/auth/persistence checks."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.brief import build_fallback_brief
from app.config import get_settings
from app.db.models import (
    CheckinScore,
    Device,
    FleetAlert,
    HelpRequest,
    NearMiss,
    NearMissMedia,
    Notice,
    PairingCode,
)

# Minimal JPEG SOI…EOI
_MINI_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00" + bytes([16] * 64) + b"\xff\xc0\x00\x0b\x08\x00\x01"
    b"\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff"
    b"\xda\x00\x08\x01\x01\x00\x00?\x00\x7f\xff\xd9"
)


async def _staff_headers(client: AsyncClient) -> dict[str, str]:
    r = await client.post("/api/v1/auth/login", json={"username": "master", "pin": "1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _crew_headers(client: AsyncClient, session: AsyncSession) -> dict[str, str]:
    now = datetime.now(UTC)
    code = "CREW-TEST"
    session.add(
        PairingCode(
            code=code,
            created_at=now,
            expires_at=now + timedelta(hours=24),
            active=True,
        )
    )
    await session.commit()
    pair = await client.post(
        "/api/v1/auth/pair",
        json={"join_code": code, "vessel_id": "VSL-DEMO01", "language": "en"},
    )
    assert pair.status_code == 200, pair.text
    return {"Authorization": f"Bearer {pair.json()['device_token']}"}


async def _seed_ship_data(session: AsyncSession) -> dict[str, Any]:
    """Minimal realistic data for ship endpoint tests."""
    settings = get_settings()
    media_root = Path(settings.data_dir) / "media"
    media_root.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    existing = (
        await session.execute(select(PairingCode).where(PairingCode.code == "7Q4K-9XPL"))
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            PairingCode(
                code="7Q4K-9XPL",
                created_at=now,
                expires_at=now + timedelta(hours=24),
                active=True,
            )
        )

    rr = "anon-aabbccddeeff0011"
    session.add(
        Device(
            reporter_ref=rr,
            rank_group="deck_rating",
            language="hi",
            device_label="test-pixel",
            paired_at=now,
            revoked=False,
        )
    )

    record_id = uuid.uuid4()
    media_id = uuid.uuid4()
    session.add(
        NearMiss(
            record_id=record_id,
            client_id=f"test-nm-{record_id.hex[:12]}",
            reporter_ref=rr,
            rank_group="deck_rating",
            created_at=now - timedelta(hours=3),
            occurred_at=now - timedelta(hours=4),
            source="photo",
            original_language="en",
            original_text="Oil on deck near crane pedestal.",
            english_text="Oil on deck near crane pedestal.",
            area="crane_area",
            area_detail="crane 1",
            hazard_type="slip_trip_fall",
            ism_report_type="near_miss",
            severity_level="high",
            potential_consequence="serious_injury",
            recurring=True,
            description="Oil spill near crane pedestal creating slip hazard.",
            needs_clarification=False,
            extraction={"model": "seed", "confidence": 0.9, "status": "structured", "attempts": 1},
            state="confirmed",
            status="open",
            synced_to_shore=False,
            embedding=None,
        )
    )
    dest_dir = media_root / str(record_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{media_id}.jpg"
    dest.write_bytes(_MINI_JPEG)
    session.add(
        NearMissMedia(
            media_id=media_id,
            record_id=record_id,
            kind="photo",
            path=str(dest.resolve()),
            uploaded_to_shore=False,
        )
    )

    session.add(
        NearMiss(
            record_id=uuid.uuid4(),
            client_id=f"test-nm-med-{uuid.uuid4().hex[:8]}",
            reporter_ref="anon-1122334455667788",
            rank_group="engine_rating",
            created_at=now - timedelta(days=1),
            source="text",
            original_language="en",
            original_text="Loose grating in engine room.",
            english_text="Loose grating in engine room.",
            area="engine_room",
            area_detail=None,
            hazard_type="slip_trip_fall",
            ism_report_type="hazardous_situation",
            severity_level="medium",
            potential_consequence="first_aid",
            recurring=False,
            description="Loose grating in engine room walkway.",
            needs_clarification=False,
            extraction={"model": "seed", "confidence": 0.8, "status": "structured", "attempts": 1},
            state="confirmed",
            status="open",
            synced_to_shore=False,
        )
    )

    today = date.today()
    for i in range(6):
        session.add(
            CheckinScore(
                checkin_id=uuid.uuid4(),
                reporter_ref=f"anon-{i:016x}",
                rank_group="deck_rating",
                date=today,
                language="en",
                mood=5 + i % 3,
                fatigue=6,
                workload=5,
                themes=["sleep"],
                source="quick",
                rail_triggered=False,
            )
        )

    alert_id = uuid.uuid4()
    session.add(
        FleetAlert(
            alert_id=alert_id,
            cluster_id="CLU-TEST",
            title="Test fleet alert",
            body_en="Pattern across sister vessels.",
            severity="high",
            linked_cases=["SYN-ACC-001"],
            received_at=now,
            read_at=None,
        )
    )

    esc_id = uuid.uuid4()
    session.add(
        HelpRequest(
            escalation_id=esc_id,
            reporter_ref=rr,
            category="medical",
            consent_to_contact=True,
            created_at=now,
            status="open",
        )
    )

    notice_id = uuid.uuid4()
    session.add(
        Notice(
            notice_id=notice_id,
            created_by_role="master",
            title_en="Seed notice",
            body_en="Wear PPE near the crane.",
            priority="urgent",
            created_at=now,
            source="ship",
        )
    )

    await session.commit()
    return {
        "record_id": str(record_id),
        "media_id": str(media_id),
        "alert_id": str(alert_id),
        "escalation_id": str(esc_id),
        "notice_id": str(notice_id),
    }


@pytest.mark.asyncio
async def test_ship_endpoints_happy_path(client: AsyncClient, session: AsyncSession):
    ids = await _seed_ship_data(session)
    h = await _staff_headers(client)

    ov = await client.get("/api/v1/ship/overview", headers=h)
    assert ov.status_code == 200, ov.text
    body = ov.json()
    assert body["vessel"]["id"] == "VSL-DEMO01"
    assert body["today"]["open_hazards"] >= 1
    assert body["today"]["high_or_critical_open"] >= 1
    assert body["fleet_alerts_unread"] >= 1
    assert body["medical_alerts_open"] >= 1
    assert body["model"]["ready"] is False

    lst = await client.get("/api/v1/ship/near-misses", headers=h)
    assert lst.status_code == 200
    items = lst.json()["items"]
    assert len(items) >= 2
    assert all(i["similar_onboard"] == 0 for i in items)

    filtered = await client.get(
        "/api/v1/ship/near-misses",
        headers=h,
        params={"severity": "high", "status": "open"},
    )
    assert filtered.status_code == 200
    assert all(i["severity_level"] == "high" for i in filtered.json()["items"])

    detail = await client.get(f"/api/v1/ship/near-misses/{ids['record_id']}", headers=h)
    assert detail.status_code == 200, detail.text
    assert detail.json()["photos"][0]["url"] == f"/api/v1/ship/media/{ids['media_id']}"

    media = await client.get(f"/api/v1/ship/media/{ids['media_id']}", headers=h)
    assert media.status_code == 200
    assert media.headers["content-type"].startswith("image/jpeg")

    wb = await client.get("/api/v1/ship/wellbeing/summary", headers=h, params={"days": 7})
    assert wb.status_code == 200
    assert wb.json()["k_threshold"] == 5

    brief = await client.get("/api/v1/ship/brief/today", headers=h)
    assert brief.status_code == 200
    assert brief.json()["source"] == "edge"

    notices = await client.get("/api/v1/ship/notices", headers=h)
    assert notices.status_code == 200
    assert any(n["title_en"] == "Seed notice" for n in notices.json()["items"])

    fa = await client.get("/api/v1/ship/fleet-alerts", headers=h)
    assert fa.status_code == 200
    assert len(fa.json()["items"]) >= 1

    med = await client.get("/api/v1/ship/medical-alerts", headers=h)
    assert med.status_code == 200
    assert med.json()["items"][0]["rank_group"] == "deck_rating"


# --- Required coverage checks -------------------------------------------------


@pytest.mark.asyncio
async def test_k_anonymity_4_suppressed_5_visible(client: AsyncClient, session: AsyncSession):
    """1. k-anon: 4 reporters on a day → suppressed; 5 → visible."""
    h = await _staff_headers(client)
    today = date.today()
    day4 = today - timedelta(days=2)
    for i in range(4):
        session.add(
            CheckinScore(
                checkin_id=uuid.uuid4(),
                reporter_ref=f"anon-{0x4000 + i:016x}",
                rank_group="deck_rating",
                date=day4,
                language="en",
                mood=5,
                fatigue=5,
                workload=5,
                source="quick",
                rail_triggered=False,
            )
        )
    day5 = today - timedelta(days=1)
    for i in range(5):
        session.add(
            CheckinScore(
                checkin_id=uuid.uuid4(),
                reporter_ref=f"anon-{0x5000 + i:016x}",
                rank_group="deck_rating",
                date=day5,
                language="en",
                mood=6,
                fatigue=7,
                workload=6,
                themes=["sleep"],
                source="quick",
                rail_triggered=False,
            )
        )
    await session.commit()

    r = await client.get("/api/v1/ship/wellbeing/summary", headers=h, params={"days": 7})
    assert r.status_code == 200
    by_date = {row["date"]: row for row in r.json()["daily"]}
    assert by_date[day4.isoformat()]["n"] == 4
    assert by_date[day4.isoformat()]["suppressed"] is True
    assert by_date[day4.isoformat()]["mood_avg"] is None
    assert by_date[day5.isoformat()]["n"] == 5
    assert by_date[day5.isoformat()]["suppressed"] is False
    assert by_date[day5.isoformat()]["mood_avg"] == 6.0


@pytest.mark.asyncio
async def test_reporter_ref_absent_from_all_ship_json_bodies(
    client: AsyncClient, session: AsyncSession
):
    """2. reporter_ref never appears anywhere in any /ship/* JSON response body."""
    ids = await _seed_ship_data(session)
    h = await _staff_headers(client)
    rid, mid, aid, eid = (
        ids["record_id"],
        ids["media_id"],
        ids["alert_id"],
        ids["escalation_id"],
    )

    calls: list[tuple[str, str, dict | None]] = [
        ("GET", "/api/v1/ship/pairing-qr", None),
        ("POST", "/api/v1/ship/pairing-qr/rotate", None),
        ("GET", "/api/v1/ship/overview", None),
        ("GET", "/api/v1/ship/near-misses", None),
        ("GET", f"/api/v1/ship/near-misses/{rid}", None),
        (
            "PATCH",
            f"/api/v1/ship/near-misses/{rid}",
            {
                "status": "action_assigned",
                "action_text_en": "Inspect hose",
                "action_owner_rank": "bosun",
                "action_due": "2026-10-20",
            },
        ),
        ("GET", "/api/v1/ship/wellbeing/summary", None),
        ("GET", "/api/v1/ship/brief/today", None),
        ("POST", "/api/v1/ship/brief/regenerate", None),
        ("GET", "/api/v1/ship/notices", None),
        (
            "POST",
            "/api/v1/ship/notices",
            {"title_en": "Notice", "body_en": "Body", "priority": "normal"},
        ),
        ("GET", "/api/v1/ship/fleet-alerts", None),
        ("POST", f"/api/v1/ship/fleet-alerts/{aid}/read", None),
        ("GET", "/api/v1/ship/medical-alerts", None),
        ("POST", f"/api/v1/ship/medical-alerts/{eid}/ack", None),
    ]

    for method, path, body in calls:
        if method == "GET":
            r = await client.get(path, headers=h)
        elif method == "POST":
            r = await client.post(path, headers=h, json=body)
        else:
            r = await client.patch(path, headers=h, json=body)
        assert r.status_code in (200, 201), f"{method} {path} → {r.status_code} {r.text}"
        # Scan raw JSON text (not just object keys)
        assert "reporter_ref" not in r.text, f"reporter_ref leaked in {method} {path}: {r.text}"

    # Media is binary — still must not leak the string if somehow wrapped
    media = await client.get(f"/api/v1/ship/media/{mid}", headers=h)
    assert media.status_code == 200
    assert b"reporter_ref" not in media.content


@pytest.mark.asyncio
async def test_crew_token_403_on_every_ship_route(client: AsyncClient, session: AsyncSession):
    """3. crew token → 403 on every /ship/* route."""
    ids = await _seed_ship_data(session)
    crew_h = await _crew_headers(client, session)
    rid, mid, aid, eid = (
        ids["record_id"],
        ids["media_id"],
        ids["alert_id"],
        ids["escalation_id"],
    )

    calls: list[tuple[str, str, dict | None]] = [
        ("GET", "/api/v1/ship/pairing-qr", None),
        ("POST", "/api/v1/ship/pairing-qr/rotate", None),
        ("GET", "/api/v1/ship/overview", None),
        ("GET", "/api/v1/ship/near-misses", None),
        ("GET", f"/api/v1/ship/near-misses/{rid}", None),
        (
            "PATCH",
            f"/api/v1/ship/near-misses/{rid}",
            {"status": "closed"},
        ),
        ("GET", f"/api/v1/ship/media/{mid}", None),
        ("GET", "/api/v1/ship/wellbeing/summary", None),
        ("GET", "/api/v1/ship/brief/today", None),
        ("POST", "/api/v1/ship/brief/regenerate", None),
        ("GET", "/api/v1/ship/notices", None),
        (
            "POST",
            "/api/v1/ship/notices",
            {"title_en": "x", "body_en": "y", "priority": "normal"},
        ),
        ("GET", "/api/v1/ship/fleet-alerts", None),
        ("POST", f"/api/v1/ship/fleet-alerts/{aid}/read", None),
        ("GET", "/api/v1/ship/medical-alerts", None),
        ("POST", f"/api/v1/ship/medical-alerts/{eid}/ack", None),
    ]

    for method, path, body in calls:
        if method == "GET":
            r = await client.get(path, headers=crew_h)
        elif method == "POST":
            r = await client.post(path, headers=crew_h, json=body)
        else:
            r = await client.patch(path, headers=crew_h, json=body)
        assert r.status_code == 403, f"{method} {path} expected 403, got {r.status_code}"


def test_fallback_brief_validates_against_master_brief_schema():
    """4. fallback brief validates against contracts/schemas/master_brief.schema.json."""
    schema_path = Path(get_settings().contracts_dir) / "schemas" / "master_brief.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = build_fallback_brief(
        {
            "vessel_id": "VSL-DEMO01",
            "brief_date": "2026-10-17",
            "wellbeing": {
                "k_ok": True,
                "n": 8,
                "mood_avg": 5.5,
                "fatigue_avg": 6.2,
                "trend": "declining",
            },
            "open_hazards": [
                {
                    "hazard_type": "slip_trip_fall",
                    "area": "crane_area",
                    "count_7d": 2,
                    "fleet_cluster_id": None,
                    "linked_cases": [],
                }
            ],
            "evidence_refs": ["6f1d2c1e-8a2b-4c3d-9e4f-0a1b2c3d4e03"],
        }
    )
    jsonschema.validate(payload, schema)
    assert payload["provenance"]["model"] == "deterministic-fallback"


@pytest.mark.asyncio
async def test_patch_near_miss_persisted_and_visible_on_get(
    client: AsyncClient, session: AsyncSession
):
    """5. PATCH near-miss → status/action persisted and visible in GET."""
    ids = await _seed_ship_data(session)
    h = await _staff_headers(client)
    rid = ids["record_id"]

    patched = await client.patch(
        f"/api/v1/ship/near-misses/{rid}",
        headers=h,
        json={
            "status": "action_assigned",
            "action_text_en": "Fit drip tray and replace hose",
            "action_owner_rank": "bosun",
            "action_due": "2026-10-20",
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "action_assigned"

    got = await client.get(f"/api/v1/ship/near-misses/{rid}", headers=h)
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["status"] == "action_assigned"
    assert body["action_text_en"] == "Fit drip tray and replace hose"
    assert body["action_owner_rank"] == "bosun"
    assert body["action_due"] == "2026-10-20"
    assert "reporter_ref" not in got.text
