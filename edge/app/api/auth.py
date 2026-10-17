"""POST /auth/pair, POST /auth/login, GET /me."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.auth.deps import AuthPrincipal, get_principal
from app.auth.pairing import new_reporter_ref, validate_join_code
from app.auth.staff import authenticate, is_locked
from app.auth.tokens import issue_device_token, issue_staff_token
from app.config import get_settings
from app.db.models import Device
from app.db.session import get_session
from app.errors import AppError

router = APIRouter(tags=["auth"])

RankGroup = Literal[
    "deck_officer",
    "engine_officer",
    "deck_rating",
    "engine_rating",
    "catering",
    "cadet",
    "undisclosed",
]


class PairRequest(BaseModel):
    join_code: str
    vessel_id: str
    device_label: str | None = None
    language: str = "en"
    rank_group: RankGroup = "undisclosed"


class PairResponse(BaseModel):
    device_token: str
    reporter_ref: str
    vessel_id: str
    vessel_name: str
    edge_version: str


class LoginRequest(BaseModel):
    username: str
    pin: str = Field(min_length=1, max_length=32)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    vessel_id: str
    vessel_name: str


class MeResponse(BaseModel):
    role: str
    vessel_id: str
    reporter_ref: str | None = None
    username: str | None = None


@router.post("/auth/pair", response_model=PairResponse)
async def pair(
    body: PairRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PairResponse:
    settings = get_settings()
    if body.vessel_id != settings.vessel_id:
        raise AppError("validation_error", "Unknown vessel_id", status_code=422)

    code = await validate_join_code(session, body.join_code.strip().upper())
    if code is None:
        raise AppError("invalid_join_code", "Join code invalid or expired", status_code=401)

    device = Device(
        reporter_ref=new_reporter_ref(),
        rank_group=body.rank_group,
        language=body.language,
        device_label=body.device_label,
        paired_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        revoked=False,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)

    token = issue_device_token(
        device_id=device.id,
        reporter_ref=device.reporter_ref,
        vessel_id=settings.vessel_id,
        settings=settings,
    )
    return PairResponse(
        device_token=token,
        reporter_ref=device.reporter_ref,
        vessel_id=settings.vessel_id,
        vessel_name=settings.vessel_name,
        edge_version=__version__,
    )


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginResponse:
    settings = get_settings()
    if is_locked(body.username):
        raise AppError(
            "locked_out",
            "Too many failed PIN attempts; try again in 5 minutes",
            status_code=429,
        )

    user = await authenticate(session, body.username, body.pin)
    if user is None:
        if is_locked(body.username):
            raise AppError(
                "locked_out",
                "Too many failed PIN attempts; try again in 5 minutes",
                status_code=429,
            )
        raise AppError("invalid_credentials", "Invalid username or PIN", status_code=401)

    token = issue_staff_token(
        user_id=user.id,
        role=user.role,
        username=user.username,
        settings=settings,
    )
    return LoginResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        vessel_id=settings.vessel_id,
        vessel_name=settings.vessel_name,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    principal: Annotated[AuthPrincipal, Depends(get_principal)],
) -> MeResponse:
    settings = get_settings()
    return MeResponse(
        role=principal.role,
        vessel_id=principal.vessel_id or settings.vessel_id,
        reporter_ref=principal.reporter_ref,
        username=principal.username,
    )
