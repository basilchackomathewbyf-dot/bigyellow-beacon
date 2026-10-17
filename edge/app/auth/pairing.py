"""Per-crew pairing codes (sha256 stored) and QR payload."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from beacon_contract import new_id
from beacon_contract.edge_api import QrPayload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.crypto import normalize_pairing_code, sha256_hex
from app.config import Settings, get_settings
from app.db.models import Crew, PairingCode

# A-Z0-9 without ambiguous 0, O, 1, I (L is allowed).
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_CODE_TTL = timedelta(minutes=15)


def generate_pairing_code() -> str:
    """Format XXXX-XXXX using unambiguous alphabet."""
    chars = [secrets.choice(_ALPHABET) for _ in range(8)]
    return f"{''.join(chars[:4])}-{''.join(chars[4:])}"


def build_qr_payload(
    *,
    code: str,
    crew_id: str,
    settings: Settings | None = None,
) -> QrPayload:
    s = settings or get_settings()
    return QrPayload(
        v=1,
        edge_url=s.public_edge_url,
        vessel_id=s.vessel_id,
        vessel_name=s.vessel_name,
        code=normalize_pairing_code(code),
        crew_id=crew_id,
    )


async def create_pairing_code(
    session: AsyncSession, crew_id: str
) -> tuple[str, PairingCode]:
    """Create a one-time code. Returns (plaintext, row) — plaintext is never persisted."""
    crew = await session.get(Crew, crew_id)
    if crew is None or not crew.active:
        raise ValueError("unknown_crew")
    plaintext = generate_pairing_code()
    now = datetime.now(UTC)
    row = PairingCode(
        id=new_id(),
        code_hash=sha256_hex(normalize_pairing_code(plaintext)),
        crew_id=crew_id,
        expires_at=now + _CODE_TTL,
        used_at=None,
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return plaintext, row


class PairingCodeError(Exception):
    """Reusable / expired / unknown pairing code → HTTP 400."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


async def consume_pairing_code(
    session: AsyncSession, code: str, crew_id: str
) -> PairingCode:
    """Validate and mark used. Raises PairingCodeError on failure."""
    now = datetime.now(UTC)
    normalized = normalize_pairing_code(code)
    code_hash = sha256_hex(normalized)
    result = await session.execute(
        select(PairingCode).where(
            PairingCode.code_hash == code_hash,
            PairingCode.crew_id == crew_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise PairingCodeError("invalid")
    if row.used_at is not None:
        raise PairingCodeError("reused")
    if row.expires_at <= now:
        raise PairingCodeError("expired")
    row.used_at = now
    await session.flush()
    return row
