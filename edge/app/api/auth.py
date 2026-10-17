"""Auth routes — pairing-codes, pair, login, me, preferences, revoke device."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from beacon_contract import new_id
from beacon_contract.edge_api import (
    LoginRequest,
    MeResponse,
    PairingCodeCreate,
    PairingCodeResponse,
    PairRequest,
    PairResponse,
    PreferencesUpdate,
    SessionResponse,
)
from beacon_contract.enums import Language, RankBand, Role
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.crypto import new_device_token, sha256_hex
from app.auth.deps import AuthPrincipal, get_current_user, invalidate_device_cache, require_role
from app.auth.pairing import (
    PairingCodeError,
    build_qr_payload,
    consume_pairing_code,
    create_pairing_code,
)
from app.auth.pins import (
    clear_failures,
    hash_pin,
    lockout_remaining,
    record_failure,
    validate_pin_length,
    verify_pin,
)
from app.auth.rate_limit import check_auth_rate_limit
from app.auth.tokens import issue_session_token
from app.config import get_settings
from app.db.models import Crew, Device
from app.db.session import get_session
from app.errors import AppError

router = APIRouter(tags=["auth"])


def _crew_role(crew: Crew) -> Role:
    return Role.MASTER if crew.is_master else Role.CREW


def _me_response(crew: Crew) -> MeResponse:
    settings = get_settings()
    return MeResponse(
        crew_id=crew.id,
        display_name=crew.display_name,
        role=_crew_role(crew),
        rank=crew.rank,
        rank_band=RankBand(crew.rank_band),
        language=Language(crew.language),
        vessel_id=crew.vessel_id,
        vessel_name=settings.vessel_name,
        checkin_reminder_at=crew.checkin_reminder_at,
    )


def _locked_out(device: Device, *, retry_after: int | None = None) -> AppError:
    retry = retry_after if retry_after is not None else lockout_remaining(device)
    return AppError(
        "locked_out",
        "Too many failed PIN attempts; try again later",
        status_code=423,
        extra={"retry_after": retry},
        headers={"Retry-After": str(retry)},
    )


@router.post("/auth/pairing-codes", response_model=PairingCodeResponse)
async def create_code(
    body: PairingCodeCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
) -> PairingCodeResponse:
    crew = await session.get(Crew, body.crew_id)
    if crew is None or not crew.active:
        raise AppError("not_found", "Crew member not found", status_code=404)
    try:
        plaintext, row = await create_pairing_code(session, body.crew_id)
    except ValueError as exc:
        raise AppError("not_found", "Crew member not found", status_code=404) from exc
    await session.commit()
    return PairingCodeResponse(
        code=plaintext,
        crew_id=crew.id,
        display_name=crew.display_name,
        qr_payload=build_qr_payload(code=plaintext, crew_id=crew.id),
        expires_at=row.expires_at,
    )


@router.post("/auth/pair", response_model=PairResponse)
async def pair(
    request: Request,
    body: PairRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PairResponse:
    check_auth_rate_limit(request)
    settings = get_settings()

    crew = await session.get(Crew, body.crew_id)
    if crew is None or not crew.active:
        raise AppError("not_found", "Crew member not found", status_code=404)

    if not validate_pin_length(body.pin, is_master=crew.is_master):
        expected = 6 if crew.is_master else 4
        raise AppError(
            "validation_error",
            f"PIN must be {expected} digits for this role",
            status_code=422,
        )

    try:
        await consume_pairing_code(session, body.pairing_code, body.crew_id)
    except PairingCodeError as exc:
        raise AppError(
            "invalid_pairing_code",
            "Pairing code invalid, expired, or already used",
            status_code=400,
        ) from exc

    now = datetime.now(UTC)
    crew.pin_hash = hash_pin(body.pin)
    device_token = new_device_token()
    device = Device(
        id=new_id(),
        crew_id=crew.id,
        token_hash=sha256_hex(device_token),
        paired_at=now,
        last_seen_at=now,
        revoked=False,
    )
    session.add(device)
    await session.commit()

    return PairResponse(
        device_id=device.id,
        device_token=device_token,
        crew_id=crew.id,
        role=_crew_role(crew),
        vessel_id=settings.vessel_id,
    )


@router.post("/auth/login", response_model=SessionResponse)
async def login(
    request: Request,
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SessionResponse:
    check_auth_rate_limit(request)
    settings = get_settings()

    token_hash = sha256_hex(body.device_token)
    result = await session.execute(select(Device).where(Device.token_hash == token_hash))
    device = result.scalar_one_or_none()
    if device is None or device.revoked:
        raise AppError("invalid_token", "Device revoked or unknown", status_code=401)

    remaining = lockout_remaining(device)
    if remaining > 0:
        await session.commit()
        raise _locked_out(device, retry_after=remaining)
    # Expired lock may have been cleared above — persist that.
    await session.flush()

    crew = await session.get(Crew, device.crew_id)
    if crew is None or not crew.active or not crew.pin_hash:
        raise AppError("invalid_credentials", "Invalid PIN", status_code=401)

    if not verify_pin(crew.pin_hash, body.pin):
        retry = record_failure(device)
        await session.commit()
        if retry > 0:
            raise _locked_out(device, retry_after=retry)
        raise AppError("invalid_credentials", "Invalid PIN", status_code=401)

    clear_failures(device)
    device.last_seen_at = datetime.now(UTC)
    await session.commit()

    role = _crew_role(crew)
    access_token, expires_at = issue_session_token(
        crew_id=crew.id,
        role=role.value,
        vessel_id=settings.vessel_id,
        device_id=device.id,
        settings=settings,
    )
    return SessionResponse(
        access_token=access_token,
        expires_at=expires_at,
        role=role,
        crew_id=crew.id,
        vessel_id=settings.vessel_id,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> MeResponse:
    return _me_response(principal.crew)


@router.put("/me/preferences", response_model=MeResponse)
async def update_preferences(
    body: PreferencesUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> MeResponse:
    crew = principal.crew
    if body.language is not None:
        crew.language = body.language.value
    if body.checkin_reminder_at is not None:
        crew.checkin_reminder_at = body.checkin_reminder_at
    await session.commit()
    await session.refresh(crew)
    return _me_response(crew)


@router.delete("/auth/devices/{device_id}", status_code=204)
async def revoke_device(
    device_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(require_role("master"))],
) -> None:
    result = await session.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        raise AppError("not_found", "Device not found", status_code=404)
    device.revoked = True
    await session.commit()
    invalidate_device_cache(device_id)
