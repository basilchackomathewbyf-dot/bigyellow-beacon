"""Ship staff endpoints — E1: pairing QR only."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, require_role
from app.auth.pairing import (
    build_qr_payload,
    count_paired_devices,
    create_pairing_code,
    resolve_or_create_active_code,
)
from app.db.session import get_session

router = APIRouter(prefix="/ship", tags=["ship"])


def _qr_response(code_row: Any, paired: int) -> dict[str, Any]:
    return {
        "qr_payload": build_qr_payload(code_row.code),
        "join_code": code_row.code,
        "expires_at": code_row.expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "paired_devices": paired,
    }


@router.get("/pairing-qr")
async def pairing_qr(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[AuthPrincipal, Depends(require_role("master", "safety_officer"))],
) -> dict[str, Any]:
    code = await resolve_or_create_active_code(session)
    paired = await count_paired_devices(session)
    await session.commit()
    return _qr_response(code, paired)


@router.post("/pairing-qr/rotate")
async def pairing_qr_rotate(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[AuthPrincipal, Depends(require_role("master", "safety_officer"))],
) -> dict[str, Any]:
    code = await create_pairing_code(session)
    paired = await count_paired_devices(session)
    await session.commit()
    return _qr_response(code, paired)
