"""Ship staff API — pairing QR + §8 endpoints. Roles: master | safety_officer."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, require_role
from app.auth.pairing import (
    build_qr_payload,
    count_paired_devices,
    create_pairing_code,
    resolve_or_create_active_code,
)
from app.config import get_settings
from app.db.models import (
    Device,
    FleetAlert,
    HelpRequest,
    NearMiss,
    NearMissMedia,
    Notice,
    NoticeAck,
    NoticeTranslation,
    Outbox,
    SyncState,
)
from app.db.session import get_session
from app.errors import AppError
from app.services import brief_service, near_miss_service, wellbeing_service

logger = logging.getLogger("beacon.ship")

router = APIRouter(prefix="/ship", tags=["ship"])

StaffDep = Annotated[AuthPrincipal, Depends(require_role("master", "safety_officer"))]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _qr_response(code_row: Any, paired: int) -> dict[str, Any]:
    return {
        "qr_payload": build_qr_payload(code_row.code),
        "join_code": code_row.code,
        "expires_at": code_row.expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "paired_devices": paired,
    }


def _fmt_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _sync_value(session: AsyncSession, key: str) -> str | None:
    result = await session.execute(select(SyncState).where(SyncState.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


# --- Pairing (E1) -----------------------------------------------------------


@router.get("/pairing-qr")
async def pairing_qr(session: SessionDep, _: StaffDep) -> dict[str, Any]:
    code = await resolve_or_create_active_code(session)
    paired = await count_paired_devices(session)
    await session.commit()
    return _qr_response(code, paired)


@router.post("/pairing-qr/rotate")
async def pairing_qr_rotate(session: SessionDep, _: StaffDep) -> dict[str, Any]:
    code = await create_pairing_code(session)
    paired = await count_paired_devices(session)
    await session.commit()
    return _qr_response(code, paired)


# --- Overview ---------------------------------------------------------------


@router.get("/overview")
async def overview(session: SessionDep, _: StaffDep) -> dict[str, Any]:
    settings = get_settings()
    since_24h = datetime.now(UTC) - timedelta(hours=24)

    reports_24h = int(
        (
            await session.execute(
                select(func.count())
                .select_from(NearMiss)
                .where(NearMiss.state == "confirmed", NearMiss.created_at >= since_24h)
            )
        ).scalar_one()
    )
    open_hazards, high_or_critical = await brief_service.open_hazard_counts(session)
    checkins_today = await wellbeing_service.checkins_today_count(session)
    crew_paired = await count_paired_devices(session)
    wellbeing = await wellbeing_service.today_snapshot(session)

    link_mode = (await _sync_value(session, "link_mode")) or settings.link_mode
    last_link_ok = await _sync_value(session, "last_link_ok_at")
    last_sync_at = await _sync_value(session, "last_sync_at")
    shore_link = "down"
    if link_mode != "forced_down" and last_link_ok:
        shore_link = "up"

    pending = int(
        (
            await session.execute(
                select(func.count()).select_from(Outbox).where(Outbox.sent_at.is_(None))
            )
        ).scalar_one()
    )

    fleet_unread = int(
        (
            await session.execute(
                select(func.count()).select_from(FleetAlert).where(FleetAlert.read_at.is_(None))
            )
        ).scalar_one()
    )
    medical_open = int(
        (
            await session.execute(
                select(func.count())
                .select_from(HelpRequest)
                .where(HelpRequest.category == "medical", HelpRequest.status == "open")
            )
        ).scalar_one()
    )

    return {
        "vessel": {"id": settings.vessel_id, "name": settings.vessel_name},
        "today": {
            "reports_24h": reports_24h,
            "open_hazards": open_hazards,
            "high_or_critical_open": high_or_critical,
            "checkins_today": checkins_today,
            "crew_paired": crew_paired,
        },
        "wellbeing": wellbeing,
        "link": {
            "shore_link": shore_link,
            "link_mode": link_mode,
            "last_sync_at": last_sync_at,
            "pending_items": pending,
        },
        "fleet_alerts_unread": fleet_unread,
        "medical_alerts_open": medical_open,
        # E4: model server not ready yet
        "model": {"ready": False, "name": "gemma-3n-E4B-it"},
    }


# --- Near-misses ------------------------------------------------------------


@router.get("/near-misses")
async def list_near_misses(
    session: SessionDep,
    _: StaffDep,
    status: str | None = None,
    area: str | None = None,
    hazard_type: str | None = None,
    severity: str | None = None,
    from_: Annotated[str | None, Query(alias="from")] = None,
    to: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    def _parse(iso: str | None) -> datetime | None:
        if not iso:
            return None
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AppError("validation_error", f"Invalid datetime: {iso}", status_code=422) from exc

    return await near_miss_service.list_near_misses(
        session,
        status=status,
        area=area,
        hazard_type=hazard_type,
        severity=severity,
        from_dt=_parse(from_),
        to_dt=_parse(to),
        limit=limit,
        cursor=cursor,
    )


@router.get("/near-misses/{record_id}")
async def get_near_miss(
    record_id: UUID, session: SessionDep, _: StaffDep
) -> dict[str, Any]:
    return await near_miss_service.get_near_miss(session, record_id)


class PatchNearMissBody(BaseModel):
    status: Literal["open", "action_assigned", "closed"] | None = None
    action_text_en: str | None = None
    action_owner_rank: str | None = None
    action_due: date | None = None


@router.patch("/near-misses/{record_id}")
async def patch_near_miss(
    record_id: UUID,
    body: PatchNearMissBody,
    session: SessionDep,
    _: StaffDep,
) -> dict[str, Any]:
    return await near_miss_service.patch_near_miss(
        session,
        record_id,
        status=body.status,
        action_text_en=body.action_text_en,
        action_owner_rank=body.action_owner_rank,
        action_due=body.action_due,
    )


@router.get("/media/{media_id}")
async def get_media(media_id: UUID, session: SessionDep, _: StaffDep) -> FileResponse:
    result = await session.execute(
        select(NearMissMedia).where(NearMissMedia.media_id == media_id)
    )
    media = result.scalar_one_or_none()
    if media is None:
        raise AppError("not_found", "Media not found", status_code=404)
    path = Path(media.path)
    if not path.is_file():
        raise AppError("not_found", "Media file missing", status_code=404)
    return FileResponse(path, media_type="image/jpeg", filename=path.name)


# --- Wellbeing --------------------------------------------------------------


@router.get("/wellbeing/summary")
async def wellbeing_summary(
    session: SessionDep,
    _: StaffDep,
    days: int = Query(default=14, ge=1, le=90),
) -> dict[str, Any]:
    return await wellbeing_service.summary(session, days=days)


# --- Brief ------------------------------------------------------------------


@router.get("/brief/today")
async def brief_today(session: SessionDep, _: StaffDep) -> dict[str, Any]:
    return await brief_service.get_or_create_today(session, force=False)


@router.post("/brief/regenerate")
async def brief_regenerate(session: SessionDep, _: StaffDep) -> dict[str, Any]:
    return await brief_service.get_or_create_today(session, force=True)


# --- Notices ----------------------------------------------------------------


class CreateNoticeBody(BaseModel):
    title_en: str = Field(min_length=1, max_length=256)
    body_en: str = Field(min_length=1)
    priority: Literal["normal", "urgent"] = "normal"


async def _notice_languages(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Device.language).where(Device.revoked.is_(False)).distinct()
    )
    langs = sorted({row[0] for row in result.all() if row[0] and row[0] != "en"})
    return langs


def _schedule_notice_translations(
    notice_id: UUID, languages: list[str], title_en: str, body_en: str
) -> None:
    # TODO(E6): background translate into notice_translations for each language
    logger.info(
        "notice_translation_todo notice_id=%s languages=%s",
        notice_id,
        ",".join(languages),
    )


@router.get("/notices")
async def list_notices(session: SessionDep, _: StaffDep) -> dict[str, Any]:
    result = await session.execute(select(Notice).order_by(Notice.created_at.desc()))
    notices = list(result.scalars().all())
    recipients = await count_paired_devices(session)
    items = []
    for n in notices:
        acks = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(NoticeAck)
                    .where(NoticeAck.notice_id == n.notice_id)
                )
            ).scalar_one()
        )
        langs_result = await session.execute(
            select(NoticeTranslation.lang).where(NoticeTranslation.notice_id == n.notice_id)
        )
        languages = sorted({row[0] for row in langs_result.all()})
        items.append(
            {
                "notice_id": str(n.notice_id),
                "title_en": n.title_en,
                "body_en": n.body_en,
                "priority": n.priority,
                "created_at": _fmt_dt(n.created_at),
                "source": n.source,
                "acks": acks,
                "recipients": recipients,
                "languages": languages,
            }
        )
    return {"items": items}


@router.post("/notices")
async def create_notice(
    body: CreateNoticeBody,
    session: SessionDep,
    principal: StaffDep,
    background: BackgroundTasks,
) -> dict[str, Any]:
    notice = Notice(
        created_by_role=principal.role,
        title_en=body.title_en,
        body_en=body.body_en,
        priority=body.priority,
        created_at=datetime.now(UTC),
        source="ship",
    )
    session.add(notice)
    await session.commit()
    await session.refresh(notice)

    languages = await _notice_languages(session)
    background.add_task(
        _schedule_notice_translations,
        notice.notice_id,
        languages,
        body.title_en,
        body.body_en,
    )

    recipients = await count_paired_devices(session)
    return {
        "notice_id": str(notice.notice_id),
        "title_en": notice.title_en,
        "body_en": notice.body_en,
        "priority": notice.priority,
        "created_at": _fmt_dt(notice.created_at),
        "source": notice.source,
        "acks": 0,
        "recipients": recipients,
        "languages": [],
    }


# --- Fleet alerts -----------------------------------------------------------


@router.get("/fleet-alerts")
async def list_fleet_alerts(session: SessionDep, _: StaffDep) -> dict[str, Any]:
    result = await session.execute(
        select(FleetAlert).order_by(FleetAlert.received_at.desc())
    )
    items = [
        {
            "alert_id": str(a.alert_id),
            "title": a.title,
            "body_en": a.body_en,
            "severity": a.severity,
            "linked_cases": a.linked_cases or [],
            "received_at": _fmt_dt(a.received_at),
            "read_at": _fmt_dt(a.read_at),
        }
        for a in result.scalars().all()
    ]
    return {"items": items}


@router.post("/fleet-alerts/{alert_id}/read")
async def read_fleet_alert(
    alert_id: UUID, session: SessionDep, _: StaffDep
) -> dict[str, Any]:
    result = await session.execute(select(FleetAlert).where(FleetAlert.alert_id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise AppError("not_found", "Fleet alert not found", status_code=404)
    if alert.read_at is None:
        alert.read_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(alert)
    return {
        "alert_id": str(alert.alert_id),
        "title": alert.title,
        "body_en": alert.body_en,
        "severity": alert.severity,
        "linked_cases": alert.linked_cases or [],
        "received_at": _fmt_dt(alert.received_at),
        "read_at": _fmt_dt(alert.read_at),
    }


# --- Medical alerts ---------------------------------------------------------


@router.get("/medical-alerts")
async def list_medical_alerts(session: SessionDep, _: StaffDep) -> dict[str, Any]:
    result = await session.execute(
        select(HelpRequest)
        .where(HelpRequest.category == "medical")
        .order_by(HelpRequest.created_at.desc())
    )
    items = []
    for hr in result.scalars().all():
        # DECISION: rank_group from paired device; undisclosed if none
        dev = await session.execute(
            select(Device).where(Device.reporter_ref == hr.reporter_ref).limit(1)
        )
        device = dev.scalar_one_or_none()
        items.append(
            {
                "escalation_id": str(hr.escalation_id),
                "created_at": _fmt_dt(hr.created_at),
                "rank_group": device.rank_group if device else "undisclosed",
                "status": hr.status,
            }
        )
    return {"items": items}


@router.post("/medical-alerts/{escalation_id}/ack")
async def ack_medical_alert(
    escalation_id: UUID, session: SessionDep, _: StaffDep
) -> dict[str, Any]:
    result = await session.execute(
        select(HelpRequest).where(
            HelpRequest.escalation_id == escalation_id,
            HelpRequest.category == "medical",
        )
    )
    hr = result.scalar_one_or_none()
    if hr is None:
        raise AppError("not_found", "Medical alert not found", status_code=404)
    hr.status = "acked"
    await session.commit()
    await session.refresh(hr)
    dev = await session.execute(
        select(Device).where(Device.reporter_ref == hr.reporter_ref).limit(1)
    )
    device = dev.scalar_one_or_none()
    return {
        "escalation_id": str(hr.escalation_id),
        "created_at": _fmt_dt(hr.created_at),
        "rank_group": device.rank_group if device else "undisclosed",
        "status": hr.status,
    }
