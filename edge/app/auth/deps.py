"""FastAPI dependencies: get_current_user, require_role, device revoke cache."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import TYP_SESSION, decode_session_token
from app.db.models import Crew, Device
from app.db.session import get_session
from app.errors import AppError

_REVOKE_CACHE_TTL = 30.0
# device_id -> (revoked: bool, cached_at monotonic)
_revoke_cache: dict[str, tuple[bool, float]] = {}


@dataclass
class AuthPrincipal:
    crew_id: str
    role: str
    vessel_id: str
    device_id: str
    crew: Crew
    device: Device


def reset_revoke_cache() -> None:
    """Test helper."""
    _revoke_cache.clear()


def invalidate_device_cache(device_id: str) -> None:
    _revoke_cache.pop(device_id, None)


def _cache_revoked(device_id: str, revoked: bool) -> None:
    _revoke_cache[device_id] = (revoked, time.monotonic())


def _cached_revoked(device_id: str) -> bool | None:
    entry = _revoke_cache.get(device_id)
    if entry is None:
        return None
    revoked, cached_at = entry
    if time.monotonic() - cached_at > _REVOKE_CACHE_TTL:
        _revoke_cache.pop(device_id, None)
        return None
    return revoked


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token or None


async def resolve_principal(
    request: Request,
    session: AsyncSession,
    *,
    authorization: str | None = None,
    access_token: str | None = None,
) -> AuthPrincipal:
    """Resolve session JWT from Authorization Bearer, or ?access_token= on /events."""
    token = _extract_bearer(authorization)
    if token is None and request.url.path.rstrip("/").endswith("/events"):
        token = access_token
    if not token:
        raise AppError(
            "invalid_token",
            "Missing or invalid Authorization header",
            status_code=401,
        )

    try:
        payload = decode_session_token(token)
    except jwt.PyJWTError as exc:
        raise AppError("invalid_token", "Invalid token", status_code=401) from exc

    if payload.get("typ") != TYP_SESSION:
        raise AppError("invalid_token", "Session token required", status_code=401)

    crew_id = payload.get("sub")
    role = payload.get("role")
    vessel_id = payload.get("vessel_id")
    device_id = payload.get("device_id")
    if not crew_id or not role or not vessel_id or not device_id:
        raise AppError("invalid_token", "Invalid token claims", status_code=401)

    cached = _cached_revoked(device_id)
    if cached is True:
        raise AppError("invalid_token", "Device revoked or unknown", status_code=401)

    device = await session.get(Device, device_id)
    if device is None or device.crew_id != crew_id:
        _cache_revoked(device_id, True)
        raise AppError("invalid_token", "Device revoked or unknown", status_code=401)

    revoked = bool(device.revoked)
    _cache_revoked(device_id, revoked)
    if revoked:
        raise AppError("invalid_token", "Device revoked or unknown", status_code=401)

    result = await session.execute(select(Crew).where(Crew.id == crew_id, Crew.active.is_(True)))
    crew = result.scalar_one_or_none()
    if crew is None:
        raise AppError("invalid_token", "Unknown crew member", status_code=401)

    return AuthPrincipal(
        crew_id=crew_id,
        role=role,
        vessel_id=vessel_id,
        device_id=device_id,
        crew=crew,
        device=device,
    )


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Query()] = None,
) -> AuthPrincipal:
    return await resolve_principal(
        request, session, authorization=authorization, access_token=access_token
    )


# Alias used by older call sites during migration.
get_principal = get_current_user


def require_role(*roles: str):
    async def _dep(
        principal: Annotated[AuthPrincipal, Depends(get_current_user)],
    ) -> AuthPrincipal:
        if principal.role not in roles:
            raise AppError("forbidden", "Insufficient role", status_code=403)
        return principal

    return _dep
