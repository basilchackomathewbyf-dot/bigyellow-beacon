"""Ship-facing near-miss queries — never expose reporter_ref."""

from __future__ import annotations

import base64
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import NearMiss, NearMissClarification, NearMissMedia
from app.errors import AppError

_SIMILARITY_THRESHOLD = 0.8  # cosine similarity
_SIMILAR_WINDOW_DAYS = 30


def _fmt_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def encode_cursor(created_at: datetime, record_id: UUID) -> str:
    raw = f"{_fmt_dt(created_at)}|{record_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts, rid = raw.split("|", 1)
        created_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return created_at, UUID(rid)
    except Exception as exc:
        raise AppError("validation_error", "Invalid cursor", status_code=422) from exc


async def count_similar_onboard(session: AsyncSession, nm: NearMiss) -> int:
    """Confirmed records in 30 d with cosine similarity ≥ 0.8. Null embedding → 0."""
    if nm.embedding is None:
        return 0
    since = datetime.now(UTC) - timedelta(days=_SIMILAR_WINDOW_DAYS)
    # pgvector <=> is cosine distance when using vector_cosine_ops; similarity = 1 - distance
    dist_max = 1.0 - _SIMILARITY_THRESHOLD
    stmt = (
        select(func.count())
        .select_from(NearMiss)
        .where(
            NearMiss.state == "confirmed",
            NearMiss.record_id != nm.record_id,
            NearMiss.created_at >= since,
            NearMiss.embedding.is_not(None),
            NearMiss.embedding.cosine_distance(nm.embedding) <= dist_max,
        )
    )
    try:
        result = await session.execute(stmt)
        return int(result.scalar_one())
    except Exception:
        # Operator / index missing — do not fail the list endpoint
        return 0


async def list_similar(
    session: AsyncSession, nm: NearMiss, *, limit: int = 5
) -> list[dict[str, Any]]:
    if nm.embedding is None:
        return []
    since = datetime.now(UTC) - timedelta(days=_SIMILAR_WINDOW_DAYS)
    dist_max = 1.0 - _SIMILARITY_THRESHOLD
    try:
        stmt = (
            select(NearMiss)
            .where(
                NearMiss.state == "confirmed",
                NearMiss.record_id != nm.record_id,
                NearMiss.created_at >= since,
                NearMiss.embedding.is_not(None),
                NearMiss.embedding.cosine_distance(nm.embedding) <= dist_max,
            )
            .order_by(NearMiss.embedding.cosine_distance(nm.embedding))
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
    except Exception:
        return []
    return [
        {
            "record_id": str(r.record_id),
            "description": r.description,
            "created_at": _fmt_dt(r.created_at),
        }
        for r in rows
    ]


def list_item(nm: NearMiss, *, has_photos: bool, similar_onboard: int) -> dict[str, Any]:
    return {
        "record_id": str(nm.record_id),
        "created_at": _fmt_dt(nm.created_at),
        "area": nm.area,
        "area_detail": nm.area_detail,
        "hazard_type": nm.hazard_type,
        "severity_level": nm.severity_level,
        "ism_report_type": nm.ism_report_type,
        "recurring": nm.recurring,
        "description": nm.description,
        "original_language": nm.original_language,
        "rank_group": nm.rank_group,
        "has_photos": has_photos,
        "status": nm.status,
        "action_text_en": nm.action_text_en,
        "synced_to_shore": nm.synced_to_shore,
        "similar_onboard": similar_onboard,
    }


def detail_payload(
    nm: NearMiss,
    *,
    clarifications: list[NearMissClarification],
    media: list[NearMissMedia],
    similar: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "record_id": str(nm.record_id),
        "created_at": _fmt_dt(nm.created_at),
        "occurred_at": _fmt_dt(nm.occurred_at),
        "source": nm.source,
        "original_language": nm.original_language,
        "original_text": nm.original_text,
        "english_text": nm.english_text,
        "area": nm.area,
        "area_detail": nm.area_detail,
        "hazard_type": nm.hazard_type,
        "ism_report_type": nm.ism_report_type,
        "severity_level": nm.severity_level,
        "potential_consequence": nm.potential_consequence,
        "recurring": nm.recurring,
        "description": nm.description,
        "needs_clarification": nm.needs_clarification,
        "clarifying_question": nm.clarifying_question,
        "extraction": nm.extraction,
        "state": nm.state,
        "status": nm.status,
        "rank_group": nm.rank_group,
        "action_text_en": nm.action_text_en,
        "action_owner_rank": nm.action_owner_rank,
        "action_due": nm.action_due.isoformat() if nm.action_due else None,
        "synced_to_shore": nm.synced_to_shore,
        "clarifications": [
            {
                "id": str(c.id),
                "question": c.question,
                "answer_text": c.answer_text,
                "created_at": _fmt_dt(c.created_at),
            }
            for c in clarifications
        ],
        "photos": [
            {
                "media_id": str(m.media_id),
                "url": f"/api/v1/ship/media/{m.media_id}",
            }
            for m in media
            if m.kind == "photo"
        ],
        "similar": similar,
    }


async def list_near_misses(
    session: AsyncSession,
    *,
    status: str | None = None,
    area: str | None = None,
    hazard_type: str | None = None,
    severity: str | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    filters = [NearMiss.state == "confirmed"]
    if status:
        filters.append(NearMiss.status == status)
    if area:
        filters.append(NearMiss.area == area)
    if hazard_type:
        filters.append(NearMiss.hazard_type == hazard_type)
    if severity:
        filters.append(NearMiss.severity_level == severity)
    if from_dt:
        filters.append(NearMiss.created_at >= from_dt)
    if to_dt:
        filters.append(NearMiss.created_at <= to_dt)
    if cursor:
        c_at, c_id = decode_cursor(cursor)
        filters.append(
            or_(
                NearMiss.created_at < c_at,
                and_(NearMiss.created_at == c_at, NearMiss.record_id < c_id),
            )
        )

    stmt = (
        select(NearMiss)
        .where(*filters)
        .order_by(NearMiss.created_at.desc(), NearMiss.record_id.desc())
        .limit(limit + 1)
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.created_at, last.record_id)

    items = []
    for nm in rows:
        photo_count = await session.execute(
            select(func.count())
            .select_from(NearMissMedia)
            .where(NearMissMedia.record_id == nm.record_id, NearMissMedia.kind == "photo")
        )
        similar = await count_similar_onboard(session, nm)
        items.append(
            list_item(
                nm,
                has_photos=int(photo_count.scalar_one()) > 0,
                similar_onboard=similar,
            )
        )
    return {"items": items, "next_cursor": next_cursor}


async def get_near_miss(session: AsyncSession, record_id: UUID) -> dict[str, Any]:
    result = await session.execute(
        select(NearMiss)
        .where(NearMiss.record_id == record_id, NearMiss.state == "confirmed")
        .options(
            selectinload(NearMiss.media),
            selectinload(NearMiss.clarifications),
        )
    )
    nm = result.scalar_one_or_none()
    if nm is None:
        raise AppError("not_found", "Near-miss not found", status_code=404)
    similar = await list_similar(session, nm)
    return detail_payload(
        nm,
        clarifications=list(nm.clarifications),
        media=list(nm.media),
        similar=similar,
    )


async def patch_near_miss(
    session: AsyncSession,
    record_id: UUID,
    *,
    status: str | None = None,
    action_text_en: str | None = None,
    action_owner_rank: str | None = None,
    action_due: date | None = None,
) -> dict[str, Any]:
    result = await session.execute(
        select(NearMiss)
        .where(NearMiss.record_id == record_id, NearMiss.state == "confirmed")
        .options(
            selectinload(NearMiss.media),
            selectinload(NearMiss.clarifications),
        )
    )
    nm = result.scalar_one_or_none()
    if nm is None:
        raise AppError("not_found", "Near-miss not found", status_code=404)

    allowed_status = {"open", "action_assigned", "closed"}
    if status is not None:
        if status not in allowed_status:
            raise AppError("validation_error", f"Invalid status: {status}", status_code=422)
        nm.status = status
    if action_text_en is not None:
        nm.action_text_en = action_text_en
    if action_owner_rank is not None:
        nm.action_owner_rank = action_owner_rank
    if action_due is not None:
        nm.action_due = action_due

    await session.commit()
    await session.refresh(nm)
    similar = await list_similar(session, nm)
    return detail_payload(
        nm,
        clarifications=list(nm.clarifications),
        media=list(nm.media),
        similar=similar,
    )
