"""Learning feed, media cache, acks, and stats (M5)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
from beacon_contract import new_id
from beacon_contract.edge_api import (
    CheckQuestionPublic,
    LearningCard,
    LearningMediaRef,
    LearningStatsView,
)
from beacon_contract.enums import (
    InboxKind,
    LearningMediaKind,
    LearningPriority,
    RankFilter,
    SyncEntity,
    SyncOp,
)
from beacon_contract.sync import LearningStatsPayload, SyncEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import (
    Crew,
    Inbox,
    Learning,
    LearningAck,
    LearningMedia,
    LearningStats,
    Outbox,
)
from app.sync.client import ShoreClient

logger = logging.getLogger("beacon.edge.learnings")


def learnings_media_root() -> Path:
    root = Path(get_settings().data_dir) / "learnings"
    root.mkdir(parents=True, exist_ok=True)
    return root


def media_local_path(learning_id: str, media_id: str, kind: str) -> Path:
    ext = {".image": ".webp", "image": ".webp", "gif_mp4": ".mp4", "video": ".mp4"}.get(
        kind, ".bin"
    )
    folder = learnings_media_root() / learning_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{media_id}{ext}"


def media_ready(media: list[LearningMedia]) -> bool:
    """True when every media row has a cached local file (or there is no media)."""
    for m in media:
        if not m.local_path or not Path(m.local_path).is_file():
            return False
    return True


def learning_is_listable(learning: Learning, media: list[LearningMedia]) -> bool:
    if learning.status != "published":
        return False
    return media_ready(media)


def _rank_matches(filter_val: str | None, rank_band: str) -> bool:
    f = RankFilter(filter_val) if filter_val else RankFilter.ALL
    if f == RankFilter.ALL:
        return True
    if f == RankFilter.OFFICERS:
        return rank_band == "officer"
    if f == RankFilter.RATINGS:
        return rank_band == "rating"
    return True


async def eligible_crew_count(session: AsyncSession, learning: Learning) -> int:
    settings = get_settings()
    rows = (
        await session.execute(
            select(Crew).where(
                Crew.vessel_id == settings.vessel_id, Crew.active.is_(True)
            )
        )
    ).scalars().all()
    return sum(1 for c in rows if _rank_matches(learning.rank_filter, c.rank_band))


async def get_or_create_stats(
    session: AsyncSession, *, learning_id: str, vessel_id: str
) -> LearningStats:
    row = (
        await session.execute(
            select(LearningStats).where(
                LearningStats.learning_id == learning_id,
                LearningStats.vessel_id == vessel_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = LearningStats(
            learning_id=learning_id,
            vessel_id=vessel_id,
            delivered=0,
            opened=0,
            acknowledged=0,
            check_correct=0,
            origin="edge",
            version=1,
        )
        session.add(row)
        await session.flush()
    return row


async def enqueue_learning_stats(
    session: AsyncSession, *, stats: LearningStats
) -> SyncEvent:
    stats.version = int(stats.version or 1) + 1
    payload = LearningStatsPayload(
        learning_id=stats.learning_id,
        vessel_id=stats.vessel_id,
        delivered=stats.delivered,
        opened=stats.opened,
        acknowledged=stats.acknowledged,
        check_correct=stats.check_correct,
    )
    event = SyncEvent(
        event_id=new_id(),
        entity=SyncEntity.LEARNING_STATS,
        op=SyncOp.UPSERT,
        entity_id=f"{stats.learning_id}:{stats.vessel_id}",
        version=stats.version,
        occurred_at=datetime.now(UTC),
        owned_fields=None,
        payload=payload.model_dump(mode="json"),
    )
    session.add(
        Outbox(
            id=event.event_id,
            entity=event.entity.value,
            entity_id=event.entity_id,
            op=event.op.value,
            payload=event.payload or {},
            version=event.version,
            created_at=event.occurred_at,
            attempts=0,
        )
    )
    return event


async def fetch_and_cache_media(
    session: AsyncSession,
    *,
    learning: Learning,
    client: ShoreClient,
    http: httpx.AsyncClient | None = None,
) -> bool:
    """
    Resolve media-url for each LearningMedia and download into DATA_DIR/learnings.
    Returns True if all media are cached (ready to show + emit learning.new).
    """
    media_rows = list(
        (
            await session.execute(
                select(LearningMedia).where(LearningMedia.learning_id == learning.id)
            )
        )
        .scalars()
        .all()
    )
    if not media_rows:
        return True

    owns = http is None
    http = http or httpx.AsyncClient(timeout=30.0)
    try:
        for m in media_rows:
            if m.local_path and Path(m.local_path).is_file():
                continue
            try:
                url_resp = await client.media_url(m.id)
                if url_resp.status_code != 200:
                    logger.warning(
                        "media_url_failed id=%s status=%s", m.id, url_resp.status_code
                    )
                    continue
                url = url_resp.json().get("url")
                if not url:
                    continue
                m.gcs_uri = url
                dl = await http.get(url)
                if dl.status_code != 200:
                    logger.warning(
                        "media_download_failed id=%s status=%s", m.id, dl.status_code
                    )
                    continue
                path = media_local_path(learning.id, m.id, m.kind)
                path.write_bytes(dl.content)
                m.local_path = str(path)
                m.bytes = len(dl.content)
            except Exception:
                logger.exception("media_cache_error media_id=%s", m.id)
    finally:
        if owns:
            await http.aclose()

    await session.flush()
    return media_ready(media_rows)


async def mark_delivered_and_inbox(
    session: AsyncSession, *, learning: Learning
) -> None:
    """Set delivered=eligible crew, inbox LEARNING items, enqueue stats."""
    settings = get_settings()
    stats = await get_or_create_stats(
        session, learning_id=learning.id, vessel_id=settings.vessel_id
    )
    n = await eligible_crew_count(session, learning)
    if stats.delivered < n:
        stats.delivered = n
        await enqueue_learning_stats(session, stats=stats)

    crew = (
        await session.execute(
            select(Crew).where(
                Crew.vessel_id == settings.vessel_id, Crew.active.is_(True)
            )
        )
    ).scalars().all()
    now = datetime.now(UTC)
    for c in crew:
        if not _rank_matches(learning.rank_filter, c.rank_band):
            continue
        session.add(
            Inbox(
                id=new_id(),
                crew_id=c.id,
                kind=InboxKind.LEARNING.value,
                ref_id=learning.id,
                title=f"New learning: {learning.title[:80]}",
                created_at=now,
            )
        )


def to_learning_card(
    learning: Learning,
    media: list[LearningMedia],
    *,
    ack: LearningAck | None,
) -> LearningCard:
    cq = learning.check_question or {}
    public = CheckQuestionPublic(
        question=cq.get("question") or "",
        options=list(cq.get("options") or ["", "", ""])[:3],
    )
    # Pad options if needed for validation
    while len(public.options) < 3:
        public.options.append("")

    refs = [
        LearningMediaRef(
            media_id=m.id,
            kind=LearningMediaKind(m.kind),
            url=f"/api/v1/learnings/{learning.id}/media/{m.id}",
            duration_s=m.duration_s,
        )
        for m in media
        if m.local_path and Path(m.local_path).is_file()
    ]
    return LearningCard(
        learning_id=learning.id,
        title=learning.title,
        context=learning.context or "",
        situation=learning.situation or "",
        do_points=list(learning.do_points or ["Follow ship SOP"]),
        dont_points=list(learning.dont_points or ["Don't skip isolation"]),
        check_question=public,
        priority=LearningPriority(learning.priority),
        media=refs,
        published_at=learning.published_at or learning.created_at,
        opened=bool(ack and ack.opened_at),
        acked=bool(ack and ack.acked_at),
    )


async def list_learning_cards(
    session: AsyncSession, *, crew_id: str, rank_band: str
) -> list[LearningCard]:
    rows = list(
        (
            await session.execute(
                select(Learning)
                .where(Learning.status == "published")
                .order_by(Learning.published_at.desc().nullslast())
            )
        )
        .scalars()
        .all()
    )
    out: list[LearningCard] = []
    for learning in rows:
        if not _rank_matches(learning.rank_filter, rank_band):
            continue
        media = list(
            (
                await session.execute(
                    select(LearningMedia).where(LearningMedia.learning_id == learning.id)
                )
            )
            .scalars()
            .all()
        )
        if not learning_is_listable(learning, media):
            continue
        ack = (
            await session.execute(
                select(LearningAck).where(
                    LearningAck.learning_id == learning.id,
                    LearningAck.crew_id == crew_id,
                )
            )
        ).scalar_one_or_none()
        out.append(to_learning_card(learning, media, ack=ack))
    return out


async def list_learning_stats(session: AsyncSession) -> list[LearningStatsView]:
    settings = get_settings()
    learnings = list(
        (
            await session.execute(
                select(Learning).where(Learning.status == "published")
            )
        )
        .scalars()
        .all()
    )
    views: list[LearningStatsView] = []
    for learning in learnings:
        media = list(
            (
                await session.execute(
                    select(LearningMedia).where(LearningMedia.learning_id == learning.id)
                )
            )
            .scalars()
            .all()
        )
        if not learning_is_listable(learning, media):
            continue
        stats = await get_or_create_stats(
            session, learning_id=learning.id, vessel_id=settings.vessel_id
        )
        crew_total = await eligible_crew_count(session, learning)
        views.append(
            LearningStatsView(
                learning_id=learning.id,
                title=learning.title,
                priority=LearningPriority(learning.priority),
                crew_total=crew_total,
                delivered=stats.delivered,
                opened=stats.opened,
                acknowledged=stats.acknowledged,
                check_correct=stats.check_correct,
            )
        )
    return views
