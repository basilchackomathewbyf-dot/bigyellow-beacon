"""JWT issue/verify (PyJWT, HS256)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from app.config import Settings, get_settings

ALGORITHM = "HS256"
# DECISION: crew device tokens have no expiry for the hackathon.
STAFF_TTL = timedelta(hours=12)


def issue_device_token(
    *,
    device_id: UUID,
    reporter_ref: str,
    vessel_id: str,
    settings: Settings | None = None,
) -> str:
    s = settings or get_settings()
    payload = {
        "sub": str(device_id),
        "role": "crew",
        "rr": reporter_ref,
        "vid": vessel_id,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, s.edge_secret, algorithm=ALGORITHM)


def issue_staff_token(
    *,
    user_id: UUID,
    role: str,
    username: str,
    settings: Settings | None = None,
) -> str:
    s = settings or get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "username": username,
        "iat": now,
        "exp": now + STAFF_TTL,
    }
    return jwt.encode(payload, s.edge_secret, algorithm=ALGORITHM)


def decode_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    s = settings or get_settings()
    return jwt.decode(token, s.edge_secret, algorithms=[ALGORITHM])
