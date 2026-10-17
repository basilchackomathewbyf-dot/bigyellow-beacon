"""Join codes and QR payload for crew device pairing."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import Device, PairingCode

# No ambiguous chars: 0/O, 1/I/L excluded.
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_CODE_TTL = timedelta(hours=24)


def generate_join_code() -> str:
    """Format XXXX-XXXX using unambiguous alphabet."""
    chars = [secrets.choice(_ALPHABET) for _ in range(8)]
    return f"{''.join(chars[:4])}-{''.join(chars[4:])}"


def new_reporter_ref() -> str:
    """Pseudonymous reporter_ref: anon- + 16 hex."""
    return "anon-" + secrets.token_hex(8)


async def create_pairing_code(session: AsyncSession) -> PairingCode:
    """Deactivate existing active codes and insert a fresh 24 h code."""
    await session.execute(update(PairingCode).where(PairingCode.active.is_(True)).values(active=False))
    now = datetime.now(UTC)
    row = PairingCode(
        code=generate_join_code(),
        created_at=now,
        expires_at=now + _CODE_TTL,
        active=True,
    )
    session.add(row)
    await session.flush()
    return row


async def get_active_pairing_code(session: AsyncSession) -> PairingCode | None:
    now = datetime.now(UTC)
    result = await session.execute(
        select(PairingCode).where(
            PairingCode.active.is_(True),
            PairingCode.expires_at > now,
        )
    )
    return result.scalar_one_or_none()


async def resolve_or_create_active_code(session: AsyncSession) -> PairingCode:
    code = await get_active_pairing_code(session)
    if code is None:
        code = await create_pairing_code(session)
    return code


def build_qr_payload(
    join_code: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    s = settings or get_settings()
    return {
        "v": 1,
        "edge": s.edge_public_url,
        "vessel_id": s.vessel_id,
        "vessel_name": s.vessel_name,
        "join_code": join_code,
    }


async def count_paired_devices(session: AsyncSession) -> int:
    result = await session.execute(select(Device).where(Device.revoked.is_(False)))
    return len(result.scalars().all())


async def validate_join_code(session: AsyncSession, code: str) -> PairingCode | None:
    now = datetime.now(UTC)
    result = await session.execute(
        select(PairingCode).where(
            PairingCode.code == code.upper(),
            PairingCode.active.is_(True),
            PairingCode.expires_at > now,
        )
    )
    return result.scalar_one_or_none()
