"""Session JWT (PyJWT, HS256). Device tokens are opaque — see crypto.new_device_token."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from beacon_contract import new_id

from app.config import Settings, get_settings

ALGORITHM = "HS256"
SESSION_TTL = timedelta(hours=12)
LEEWAY_SECONDS = 30
AUDIENCE = "beacon-app"
TYP_SESSION = "session"


def issuer_for(vessel_id: str) -> str:
    return f"beacon-edge:{vessel_id}"


def issue_session_token(
    *,
    crew_id: str,
    role: str,
    vessel_id: str,
    device_id: str,
    settings: Settings | None = None,
) -> tuple[str, datetime]:
    s = settings or get_settings()
    now = datetime.now(UTC)
    expires_at = now + SESSION_TTL
    payload = {
        "sub": crew_id,
        "role": role,
        "vessel_id": vessel_id,
        "device_id": device_id,
        "jti": new_id(),
        "iat": now,
        "exp": expires_at,
        "iss": issuer_for(vessel_id),
        "aud": AUDIENCE,
        "typ": TYP_SESSION,
    }
    token = jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM)
    return token, expires_at


def decode_session_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    s = settings or get_settings()
    return jwt.decode(
        token,
        s.jwt_secret,
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=issuer_for(s.vessel_id),
        leeway=LEEWAY_SECONDS,
        options={"require": ["sub", "role", "vessel_id", "device_id", "jti", "exp", "iat", "typ"]},
    )
