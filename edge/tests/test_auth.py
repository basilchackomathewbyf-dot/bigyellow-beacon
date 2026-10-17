"""Edge auth — contract models, pairing, PIN lockout, JWT, revoke, SSE query token."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from beacon_contract.edge_api import MeResponse, PairingCodeResponse, PairResponse, SessionResponse
from freezegun import freeze_time
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.crypto import sha256_hex
from app.auth.jwt_secret import JwtSecretError
from app.auth.pairing import create_pairing_code
from app.auth.pins import LOCKOUT_SECONDS
from app.auth.tokens import ALGORITHM, AUDIENCE, issuer_for
from app.config import get_settings
from app.db.models import Device, PairingCode
from app.db.session import get_session
from app.main import create_app


@asynccontextmanager
async def _app_client(engine) -> AsyncGenerator[AsyncClient, None]:
    application = create_app()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as s:
            yield s

    application.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    application.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_pairing_happy_path(client: AsyncClient, paired_master: dict):
    r = await client.post(
        "/api/v1/auth/pairing-codes",
        headers=paired_master["headers"],
        json={"crew_id": "c-0007-aru"},
    )
    assert r.status_code == 200, r.text
    created = PairingCodeResponse.model_validate(r.json())
    assert created.crew_id == "c-0007-aru"
    assert created.qr_payload.code == created.code
    assert created.qr_payload.crew_id == "c-0007-aru"

    pair = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": created.code, "crew_id": "c-0007-aru", "pin": "1234"},
    )
    assert pair.status_code == 200, pair.text
    body = PairResponse.model_validate(pair.json())
    assert body.role == "crew"
    assert body.device_token  # opaque, not a JWT
    assert body.device_token.count(".") != 2


@pytest.mark.asyncio
async def test_pairing_code_stored_hashed(
    client: AsyncClient, session: AsyncSession, paired_master: dict
):
    r = await client.post(
        "/api/v1/auth/pairing-codes",
        headers=paired_master["headers"],
        json={"crew_id": "c-0007-aru"},
    )
    code = r.json()["code"]
    rows = list((await session.execute(select(PairingCode))).scalars().all())
    hashes = {row.code_hash for row in rows}
    assert sha256_hex(code.upper()) in hashes
    assert code not in {getattr(row, "code", None) for row in rows}


@pytest.mark.asyncio
async def test_reused_pairing_code_400(client: AsyncClient, session: AsyncSession):
    plaintext, _ = await create_pairing_code(session, "c-0007-mst")
    await session.commit()
    ok = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": plaintext, "crew_id": "c-0007-mst", "pin": "123456"},
    )
    assert ok.status_code == 200
    again = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": plaintext, "crew_id": "c-0007-mst", "pin": "123456"},
    )
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "invalid_pairing_code"


@pytest.mark.asyncio
async def test_expired_pairing_code_400(client: AsyncClient, session: AsyncSession):
    with freeze_time("2026-10-17 12:00:00"):
        plaintext, _ = await create_pairing_code(session, "c-0007-mst")
        await session.commit()
    with freeze_time("2026-10-17 12:16:00"):
        r = await client.post(
            "/api/v1/auth/pair",
            json={"pairing_code": plaintext, "crew_id": "c-0007-mst", "pin": "123456"},
        )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_pairing_code"


@pytest.mark.asyncio
async def test_wrong_pin_length_per_role(client: AsyncClient, session: AsyncSession):
    master_code, _ = await create_pairing_code(session, "c-0007-mst")
    crew_code, _ = await create_pairing_code(session, "c-0007-aru")
    await session.commit()

    r = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": master_code, "crew_id": "c-0007-mst", "pin": "1234"},
    )
    assert r.status_code == 422

    r2 = await client.post(
        "/api/v1/auth/pair",
        json={"pairing_code": crew_code, "crew_id": "c-0007-aru", "pin": "123456"},
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_login_returns_session_response(client: AsyncClient, paired_crew: dict):
    r = await client.post(
        "/api/v1/auth/login",
        json={"device_token": paired_crew["device_token"], "pin": "1234"},
    )
    assert r.status_code == 200, r.text
    body = SessionResponse.model_validate(r.json())
    assert body.role == "crew"
    assert body.crew_id == "c-0007-aru"
    assert body.token_type == "bearer"

    settings = get_settings()
    claims = jwt.decode(
        body.access_token,
        settings.jwt_secret,
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=issuer_for(settings.vessel_id),
        leeway=30,
    )
    assert claims["sub"] == "c-0007-aru"
    assert claims["typ"] == "session"
    assert claims["device_id"] == paired_crew["device_id"]
    assert "jti" in claims


@pytest.mark.asyncio
async def test_five_bad_pins_423_then_success_after_lock(
    client: AsyncClient, paired_crew: dict, session: AsyncSession
):
    with freeze_time("2026-10-17 12:00:00") as frozen:
        for _ in range(5):
            r = await client.post(
                "/api/v1/auth/login",
                json={"device_token": paired_crew["device_token"], "pin": "9999"},
            )
        assert r.status_code == 423, r.text
        err = r.json()["error"]
        assert err["code"] == "locked_out"
        assert err["retry_after"] == LOCKOUT_SECONDS
        assert r.headers.get("retry-after") == str(LOCKOUT_SECONDS)

        device = await session.get(Device, paired_crew["device_id"])
        assert device is not None
        assert device.failed_pin_attempts == 5
        assert device.locked_until is not None

        still = await client.post(
            "/api/v1/auth/login",
            json={"device_token": paired_crew["device_token"], "pin": "1234"},
        )
        assert still.status_code == 423

        frozen.tick(delta=timedelta(seconds=LOCKOUT_SECONDS + 1))
        ok = await client.post(
            "/api/v1/auth/login",
            json={"device_token": paired_crew["device_token"], "pin": "1234"},
        )
    assert ok.status_code == 200, ok.text
    SessionResponse.model_validate(ok.json())
    await session.refresh(device)
    assert device.failed_pin_attempts == 0
    assert device.locked_until is None


@pytest.mark.asyncio
async def test_pin_lockout_survives_app_restart(engine, session: AsyncSession, paired_crew: dict):
    """failed_pin_attempts live on devices — a new app process still sees the lock."""
    async with _app_client(engine) as client1:
        for _ in range(3):
            r = await client1.post(
                "/api/v1/auth/login",
                json={"device_token": paired_crew["device_token"], "pin": "0000"},
            )
            assert r.status_code == 401

    device = await session.get(Device, paired_crew["device_id"])
    assert device is not None
    assert device.failed_pin_attempts == 3
    assert device.locked_until is None

    # New app instance (simulates process restart — in-memory state would be gone).
    async with _app_client(engine) as client2:
        for _ in range(2):
            r = await client2.post(
                "/api/v1/auth/login",
                json={"device_token": paired_crew["device_token"], "pin": "0000"},
            )
        assert r.status_code == 423, r.text
        assert r.json()["error"]["code"] == "locked_out"

        locked = await client2.post(
            "/api/v1/auth/login",
            json={"device_token": paired_crew["device_token"], "pin": "1234"},
        )
        assert locked.status_code == 423

    await session.refresh(device)
    assert device.failed_pin_attempts == 5
    assert device.locked_until is not None


@pytest.mark.asyncio
async def test_revoked_device_401(
    client: AsyncClient, paired_master: dict, paired_crew: dict, session: AsyncSession
):
    r = await client.delete(
        f"/api/v1/auth/devices/{paired_crew['device_id']}",
        headers=paired_master["headers"],
    )
    assert r.status_code == 204

    me = await client.get("/api/v1/me", headers=paired_crew["headers"])
    assert me.status_code == 401

    login = await client.post(
        "/api/v1/auth/login",
        json={"device_token": paired_crew["device_token"], "pin": "1234"},
    )
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_crew_token_403_on_master_route(client: AsyncClient, paired_crew: dict):
    r = await client.get("/api/v1/master/tickets", headers=paired_crew["headers"])
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


@pytest.mark.asyncio
async def test_tampered_and_expired_jwt_401(client: AsyncClient, paired_crew: dict):
    tampered = paired_crew["access_token"][:-4] + "xxxx"
    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401

    settings = get_settings()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "c-0007-aru",
            "role": "crew",
            "vessel_id": settings.vessel_id,
            "device_id": paired_crew["device_id"],
            "jti": "test-jti",
            "iat": now - timedelta(hours=13),
            "exp": now - timedelta(hours=1),
            "iss": issuer_for(settings.vessel_id),
            "aud": AUDIENCE,
            "typ": "session",
        },
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )
    r2 = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_sse_accepts_access_token_query(client: AsyncClient, paired_crew: dict):
    r = await client.get(
        "/api/v1/events",
        params={"access_token": paired_crew["access_token"]},
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")


def test_startup_fails_with_short_secret(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("BEACON_JWT_SECRET", "too-short")
    get_settings.cache_clear()
    with pytest.raises(JwtSecretError, match="32"):
        create_app(validate_secret=True)
    monkeypatch.setenv("BEACON_JWT_SECRET", "test-secret-at-least-32-bytes-long!!")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_no_secrets_in_logs(client: AsyncClient, session: AsyncSession, caplog):
    plaintext, _ = await create_pairing_code(session, "c-0007-mst")
    await session.commit()
    with caplog.at_level(logging.INFO):
        pair = await client.post(
            "/api/v1/auth/pair",
            json={"pairing_code": plaintext, "crew_id": "c-0007-mst", "pin": "123456"},
        )
        assert pair.status_code == 200
        device_token = pair.json()["device_token"]
        login = await client.post(
            "/api/v1/auth/login",
            json={"device_token": device_token, "pin": "123456"},
        )
        assert login.status_code == 200
        access = login.json()["access_token"]

    blob = "\n".join(rec.getMessage() for rec in caplog.records)
    blob += "\n".join(str(getattr(rec, "__dict__", {})) for rec in caplog.records)
    assert plaintext not in blob
    assert "123456" not in blob
    assert device_token not in blob
    assert access not in blob


@pytest.mark.asyncio
async def test_device_token_hash_only_in_db(
    client: AsyncClient, session: AsyncSession, paired_crew: dict
):
    device = await session.get(Device, paired_crew["device_id"])
    assert device is not None
    assert device.token_hash == sha256_hex(paired_crew["device_token"])
    assert paired_crew["device_token"] != device.token_hash


@pytest.mark.asyncio
async def test_me_and_preferences(client: AsyncClient, paired_crew: dict):
    me = await client.get("/api/v1/me", headers=paired_crew["headers"])
    assert me.status_code == 200
    body = MeResponse.model_validate(me.json())
    assert body.crew_id == "c-0007-aru"

    upd = await client.put(
        "/api/v1/me/preferences",
        headers=paired_crew["headers"],
        json={"checkin_reminder_at": "19:30"},
    )
    assert upd.status_code == 200
    assert upd.json()["checkin_reminder_at"] == "19:30"
