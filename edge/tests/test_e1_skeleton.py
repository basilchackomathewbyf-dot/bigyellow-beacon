"""E1: health, staff login, pairing + QR, /me."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.pairing import build_qr_payload
from app.auth.staff import reset_lockouts
from app.db.models import PairingCode


async def _active_code(session: AsyncSession, code: str = "7Q4K-9XPL") -> str:
    now = datetime.now(UTC)
    session.add(
        PairingCode(
            code=code,
            created_at=now,
            expires_at=now + timedelta(hours=24),
            active=True,
        )
    )
    await session.commit()
    return code


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_ready"] is False
    assert body["shore_link"] in ("up", "down")
    assert "edge_time" in body


@pytest.mark.asyncio
async def test_staff_login_and_me(client: AsyncClient):
    r = await client.post("/api/v1/auth/login", json={"username": "master", "pin": "1234"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "master"
    assert data["username"] == "master"
    assert data["vessel_id"] == "VSL-DEMO01"
    assert data["access_token"]

    me = await client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json() == {
        "role": "master",
        "vessel_id": "VSL-DEMO01",
        "reporter_ref": None,
        "username": "master",
    }


@pytest.mark.asyncio
async def test_staff_login_bad_pin(client: AsyncClient):
    r = await client.post("/api/v1/auth/login", json={"username": "master", "pin": "0000"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_staff_pin_lockout(client: AsyncClient):
    reset_lockouts()
    for _ in range(5):
        await client.post("/api/v1/auth/login", json={"username": "master", "pin": "9999"})
    r = await client.post("/api/v1/auth/login", json={"username": "master", "pin": "1234"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "locked_out"
    reset_lockouts()


@pytest.mark.asyncio
async def test_pair_and_me(client: AsyncClient, session: AsyncSession):
    code = await _active_code(session)
    r = await client.post(
        "/api/v1/auth/pair",
        json={
            "join_code": code,
            "vessel_id": "VSL-DEMO01",
            "device_label": "Pixel 7",
            "language": "hi",
            "rank_group": "deck_rating",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["vessel_id"] == "VSL-DEMO01"
    assert data["vessel_name"] == "MV Demo Star"
    assert data["reporter_ref"].startswith("anon-")
    assert len(data["reporter_ref"]) == len("anon-") + 16
    assert data["device_token"]
    assert data["edge_version"]

    me = await client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {data['device_token']}"},
    )
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "crew"
    assert body["reporter_ref"] == data["reporter_ref"]
    assert body["vessel_id"] == "VSL-DEMO01"
    assert body["username"] is None


@pytest.mark.asyncio
async def test_pair_bad_code(client: AsyncClient):
    r = await client.post(
        "/api/v1/auth/pair",
        json={"join_code": "AAAA-BBBB", "vessel_id": "VSL-DEMO01"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_join_code"


@pytest.mark.asyncio
async def test_pairing_qr_payload(client: AsyncClient, session: AsyncSession):
    await _active_code(session, "7Q4K-9XPL")
    login = await client.post(
        "/api/v1/auth/login", json={"username": "master", "pin": "1234"}
    )
    token = login.json()["access_token"]
    r = await client.get(
        "/api/v1/ship/pairing-qr",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["join_code"] == "7Q4K-9XPL"
    assert body["qr_payload"] == {
        "v": 1,
        "edge": "http://192.168.1.10:8080",
        "vessel_id": "VSL-DEMO01",
        "vessel_name": "MV Demo Star",
        "join_code": "7Q4K-9XPL",
    }
    assert body["paired_devices"] == 0
    assert "expires_at" in body


@pytest.mark.asyncio
async def test_pairing_qr_rotate(client: AsyncClient, session: AsyncSession):
    await _active_code(session, "7Q4K-9XPL")
    login = await client.post(
        "/api/v1/auth/login", json={"username": "safety", "pin": "5678"}
    )
    token = login.json()["access_token"]
    r = await client.post(
        "/api/v1/ship/pairing-qr/rotate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["join_code"] != "7Q4K-9XPL"
    assert r.json()["qr_payload"]["join_code"] == r.json()["join_code"]


@pytest.mark.asyncio
async def test_pairing_qr_requires_staff(client: AsyncClient, session: AsyncSession):
    code = await _active_code(session)
    pair = await client.post(
        "/api/v1/auth/pair",
        json={"join_code": code, "vessel_id": "VSL-DEMO01", "language": "en"},
    )
    crew_token = pair.json()["device_token"]
    r = await client.get(
        "/api/v1/ship/pairing-qr",
        headers={"Authorization": f"Bearer {crew_token}"},
    )
    assert r.status_code == 403


def test_build_qr_payload_shape():
    payload = build_qr_payload("ABCD-EFGH")
    assert payload["v"] == 1
    assert set(payload.keys()) == {"v", "edge", "vessel_id", "vessel_name", "join_code"}
