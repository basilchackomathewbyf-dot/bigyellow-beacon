"""FastAPI dependencies: current_device, require_role."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import decode_token
from app.db.models import Device, StaffUser
from app.db.session import get_session
from app.errors import AppError


@dataclass
class AuthPrincipal:
    sub: UUID
    role: str
    reporter_ref: str | None = None
    username: str | None = None
    vessel_id: str | None = None
    device: Device | None = None
    staff: StaffUser | None = None


async def _bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("invalid_token", "Missing or invalid Authorization header", status_code=401)
    return authorization.removeprefix("Bearer ").strip()


async def get_principal(
    token: Annotated[str, Depends(_bearer_token)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthPrincipal:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise AppError("invalid_token", "Invalid token", status_code=401) from exc

    role = payload.get("role")
    sub_raw = payload.get("sub")
    if not role or not sub_raw:
        raise AppError("invalid_token", "Invalid token claims", status_code=401)

    try:
        sub = UUID(str(sub_raw))
    except ValueError as exc:
        raise AppError("invalid_token", "Invalid subject", status_code=401) from exc

    if role == "crew":
        result = await session.execute(select(Device).where(Device.id == sub))
        device = result.scalar_one_or_none()
        if device is None or device.revoked:
            raise AppError("invalid_token", "Device revoked or unknown", status_code=401)
        return AuthPrincipal(
            sub=sub,
            role="crew",
            reporter_ref=device.reporter_ref,
            vessel_id=payload.get("vid"),
            device=device,
        )

    if role in ("master", "safety_officer"):
        result = await session.execute(select(StaffUser).where(StaffUser.id == sub))
        staff = result.scalar_one_or_none()
        if staff is None:
            raise AppError("invalid_token", "Unknown staff user", status_code=401)
        return AuthPrincipal(
            sub=sub,
            role=staff.role,
            username=staff.username,
            staff=staff,
        )

    raise AppError("invalid_token", "Unknown role", status_code=401)


async def current_device(
    principal: Annotated[AuthPrincipal, Depends(get_principal)],
) -> AuthPrincipal:
    if principal.role != "crew" or principal.device is None:
        raise AppError("invalid_token", "Crew device token required", status_code=401)
    return principal


def require_role(*roles: str):
    async def _dep(
        principal: Annotated[AuthPrincipal, Depends(get_principal)],
    ) -> AuthPrincipal:
        if principal.role not in roles:
            raise AppError("forbidden", "Insufficient role", status_code=403)
        return principal

    return _dep
