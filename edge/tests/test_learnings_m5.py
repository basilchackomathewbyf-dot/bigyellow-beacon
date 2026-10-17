"""M5 — learnings feed, media cache/Range, ack, stats, retract."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx
from beacon_contract import new_id
from beacon_contract.edge_api import LearningAckResult, LearningCard, LearningStatsView
from beacon_contract.enums import (
    LearningPriority,
    PullChangeType,
    SseEvent,
    SyncEntity,
)
from beacon_contract.events import master_channel, vessel_channel
from beacon_contract.sync import (
    CheckQuestion,
    LearningMediaManifest,
    LearningPublishedChange,
    LearningRetractedChange,
    PullChange,
)
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Learning, Outbox
from app.events.hub import get_hub
from app.sync.apply import apply_change
from app.sync.client import ShoreClient

LEARNING_ID = "0192f0c4-0000-7000-8000-0000000001f1"
MEDIA_ID = "0192f0c4-0000-7000-8000-0000000001e1"


def _shore_base() -> str:
    return get_settings().shore_url.rstrip("/")


def _published_change(*, with_media: bool = True) -> LearningPublishedChange:
    media = []
    if with_media:
        media = [
            LearningMediaManifest(
                media_id=MEDIA_ID,
                kind="video",  # type: ignore[arg-type]
                bytes=120,
                sha256="0" * 64,
                duration_s=5.0,
            )
        ]
    return LearningPublishedChange(
        learning_id=LEARNING_ID,
        title="Hydraulic oil on deck: stop, isolate, clean",
        context="Crane hydraulic leaks have caused slips.",
        situation="You find oil on deck near a crane pedestal.",
        do_points=["Stop crane ops", "Cordon and clean", "Report the leak"],
        dont_points=["Don't walk through oil", "Don't hose overboard", "Don't restart"],
        check_question=CheckQuestion(
            question="First thing to do when you see oil near a crane?",
            options=["Finish the job", "Stop and isolate the crane", "Wash it overboard"],
            correct_index=1,
        ),
        priority=LearningPriority.URGENT,
        rank_filter="all",  # type: ignore[arg-type]
        media=media,
        published_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def _shore_key(monkeypatch):
    monkeypatch.setenv("BEACON_SHORE_API_KEY", "demo-shore-api-key")
    get_settings.cache_clear()
    get_hub().reset()
    yield
    get_settings.cache_clear()
    get_hub().reset()


async def _apply_published(session: AsyncSession, *, with_media: bool = True) -> None:
    settings = get_settings()
    media_url = f"{_shore_base()}/mock-media/{MEDIA_ID}"
    payload = b"fake-learning-video-bytes-0123456789"

    respx.get(f"{_shore_base()}/api/v1/sync/media-url/{MEDIA_ID}").mock(
        return_value=httpx.Response(
            200,
            json={
                "media_id": MEDIA_ID,
                "url": media_url,
                "expires_at": "2030-01-01T00:00:00Z",
            },
        )
    )
    respx.get(media_url).mock(
        return_value=httpx.Response(200, content=payload, headers={"content-type": "video/mp4"})
    )

    change = PullChange(
        change_id=new_id(),
        type=PullChangeType.LEARNING_PUBLISHED,
        created_at=datetime.now(UTC),
        payload=_published_change(with_media=with_media).model_dump(mode="json"),
    )
    http = httpx.AsyncClient(base_url=_shore_base())
    client = ShoreClient(settings, client=http)
    await apply_change(session, change, client=client)
    await session.commit()
    await http.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_learning_published_cached_and_listed(
    client: AsyncClient, session: AsyncSession, paired_crew: dict
):
    await _apply_published(session)

    # Urgent → vessel:all + master channel
    replay = get_hub().replay_since(
        [vessel_channel(get_settings().vessel_id), master_channel(get_settings().vessel_id)],
        None,
    )
    assert any(m.event == SseEvent.LEARNING_NEW for m in replay)

    r = await client.get("/api/v1/learnings", headers=paired_crew["headers"])
    assert r.status_code == 200, r.text
    cards = [LearningCard.model_validate(x) for x in r.json()]
    assert len(cards) == 1
    card = cards[0]
    assert card.learning_id == LEARNING_ID
    assert card.priority == LearningPriority.URGENT
    assert len(card.media) == 1
    # correct_index must never appear on the wire
    raw = r.text
    assert "correct_index" not in raw
    assert card.check_question.options[1] == "Stop and isolate the crane"

    media = await client.get(
        f"/api/v1/learnings/{LEARNING_ID}/media/{MEDIA_ID}",
        headers=paired_crew["headers"],
    )
    assert media.status_code == 200
    assert media.content.startswith(b"fake-learning-video")


@pytest.mark.asyncio
@respx.mock
async def test_learning_hidden_until_media_cached(
    client: AsyncClient, session: AsyncSession, paired_crew: dict
):
    settings = get_settings()
    # media-url ok but download fails → not ready
    respx.get(f"{_shore_base()}/api/v1/sync/media-url/{MEDIA_ID}").mock(
        return_value=httpx.Response(
            200,
            json={
                "media_id": MEDIA_ID,
                "url": f"{_shore_base()}/mock-media/{MEDIA_ID}",
                "expires_at": "2030-01-01T00:00:00Z",
            },
        )
    )
    respx.get(f"{_shore_base()}/mock-media/{MEDIA_ID}").mock(
        return_value=httpx.Response(404)
    )

    change = PullChange(
        change_id=new_id(),
        type=PullChangeType.LEARNING_PUBLISHED,
        created_at=datetime.now(UTC),
        payload=_published_change(with_media=True).model_dump(mode="json"),
    )
    http = httpx.AsyncClient(base_url=_shore_base())
    await apply_change(session, change, client=ShoreClient(settings, client=http))
    await session.commit()
    await http.aclose()

    r = await client.get("/api/v1/learnings", headers=paired_crew["headers"])
    assert r.status_code == 200
    assert r.json() == []
    assert not any(
        m.event == SseEvent.LEARNING_NEW
        for m in get_hub().replay_since([vessel_channel(settings.vessel_id)], None)
    )


@pytest.mark.asyncio
@respx.mock
async def test_media_range_and_ack_stats_outbox(
    client: AsyncClient, session: AsyncSession, paired_crew: dict, paired_master: dict
):
    await _apply_published(session)

    ranged = await client.get(
        f"/api/v1/learnings/{LEARNING_ID}/media/{MEDIA_ID}",
        headers={**paired_crew["headers"], "Range": "bytes=0-9"},
    )
    assert ranged.status_code == 206
    assert ranged.headers["content-range"].startswith("bytes 0-9/")
    assert len(ranged.content) == 10

    ack = await client.post(
        f"/api/v1/learnings/{LEARNING_ID}/ack",
        headers=paired_crew["headers"],
        json={"opened": True, "acked": True, "check_answer": 1},
    )
    assert ack.status_code == 200, ack.text
    result = LearningAckResult.model_validate(ack.json())
    assert result.check_correct is True

    wrong = await client.post(
        f"/api/v1/learnings/{LEARNING_ID}/ack",
        headers=paired_crew["headers"],
        json={"check_answer": 0},
    )
    assert LearningAckResult.model_validate(wrong.json()).check_correct is False

    stats = await client.get(
        "/api/v1/master/learnings/stats", headers=paired_master["headers"]
    )
    assert stats.status_code == 200, stats.text
    views = [LearningStatsView.model_validate(x) for x in stats.json()]
    assert len(views) == 1
    assert views[0].opened >= 1
    assert views[0].acknowledged >= 1
    assert views[0].check_correct >= 1
    assert views[0].delivered >= 1

    session.expire_all()
    outbox = list(
        (
            await session.execute(
                select(Outbox).where(Outbox.entity == SyncEntity.LEARNING_STATS.value)
            )
        )
        .scalars()
        .all()
    )
    assert len(outbox) >= 1
    payload = outbox[-1].payload
    assert "crew_id" not in payload
    assert set(payload) >= {
        "learning_id",
        "vessel_id",
        "delivered",
        "opened",
        "acknowledged",
        "check_correct",
    }


@pytest.mark.asyncio
@respx.mock
async def test_retracted_hides_card(
    client: AsyncClient, session: AsyncSession, paired_crew: dict
):
    await _apply_published(session)
    assert (
        await client.get("/api/v1/learnings", headers=paired_crew["headers"])
    ).json()

    change = PullChange(
        change_id=new_id(),
        type=PullChangeType.LEARNING_RETRACTED,
        created_at=datetime.now(UTC),
        payload=LearningRetractedChange(
            learning_id=LEARNING_ID, retracted_at=datetime.now(UTC)
        ).model_dump(mode="json"),
    )
    http = httpx.AsyncClient(base_url=_shore_base())
    await apply_change(
        session, change, client=ShoreClient(get_settings(), client=http)
    )
    await session.commit()
    await http.aclose()

    r = await client.get("/api/v1/learnings", headers=paired_crew["headers"])
    assert r.json() == []
    learning = await session.get(Learning, LEARNING_ID)
    assert learning is not None and learning.status == "retracted"

    media = await client.get(
        f"/api/v1/learnings/{LEARNING_ID}/media/{MEDIA_ID}",
        headers=paired_crew["headers"],
    )
    assert media.status_code == 404


@pytest.mark.asyncio
async def test_crew_403_on_master_learning_stats(
    client: AsyncClient, paired_crew: dict
):
    r = await client.get(
        "/api/v1/master/learnings/stats", headers=paired_crew["headers"]
    )
    assert r.status_code == 403
