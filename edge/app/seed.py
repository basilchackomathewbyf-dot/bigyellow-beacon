"""make seed — staff, pairing code, historical near-misses, check-ins, SMS docs."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, text

from app.auth.pairing import create_pairing_code
from app.auth.staff import ensure_staff_seeded
from app.config import get_settings
from app.db.models import (
    CheckinScore,
    Doc,
    DocChunk,
    NearMiss,
    PairingCode,
    SyncState,
)
from app.db import session as db_session
from app.logging import setup_logging

logger = logging.getLogger("beacon.seed")

# Historical near-misses for VSL-DEMO01 — NOT the crane demo record.
_HISTORICAL_NEAR_MISSES = [
    {
        "area": "engine_room",
        "area_detail": "near purifier",
        "hazard_type": "slip_trip_fall",
        "ism_report_type": "near_miss",
        "severity_level": "medium",
        "potential_consequence": "first_aid",
        "recurring": False,
        "original_language": "en",
        "original_text": "Oil residue on the deck plating by the fuel oil purifier; almost slipped.",
        "english_text": "Oil residue on the deck plating by the fuel oil purifier; almost slipped.",
        "description": "Near slip on oil residue near the fuel oil purifier in the engine room.",
        "rank_group": "engine_rating",
        "source": "text",
    },
    {
        "area": "mooring_station",
        "area_detail": "aft",
        "hazard_type": "mooring_ops",
        "ism_report_type": "hazardous_situation",
        "severity_level": "high",
        "potential_consequence": "serious_injury",
        "recurring": False,
        "original_language": "tl",
        "original_text": "May snap-back zone na walang marker sa aft mooring.",
        "english_text": "Snap-back zone at aft mooring has no marker.",
        "description": "Missing snap-back zone marking at the aft mooring station.",
        "rank_group": "deck_rating",
        "source": "voice",
    },
    {
        "area": "accommodation_ladder",
        "area_detail": None,
        "hazard_type": "ladder_access",
        "ism_report_type": "near_miss",
        "severity_level": "medium",
        "potential_consequence": "lost_time_injury",
        "recurring": True,
        "original_language": "hi",
        "original_text": "सीढ़ी की रेल ढीली है, उतरते समय संभल गया।",
        "english_text": "Accommodation ladder rail is loose; I caught myself while descending.",
        "description": "Loose rail on accommodation ladder during descent.",
        "rank_group": "deck_officer",
        "source": "voice",
    },
]

# 8 fake reporter_refs so wellbeing charts clear k=5
_REPORTER_REFS = [f"anon-{i:016x}" for i in range(1, 9)]


def _chunk_text(text_body: str, size: int = 800, overlap: int = 100) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text_body):
        end = min(start + size, len(text_body))
        chunks.append(text_body[start:end])
        if end >= len(text_body):
            break
        start = max(0, end - overlap)
    return chunks or [text_body]


async def run_seed() -> None:
    setup_logging()
    get_settings.cache_clear()
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db_session.init_engine(settings.database_url)
    assert db_session.async_session_factory is not None

    async with db_session.async_session_factory() as session:
        # Ensure pgvector extension (idempotent)
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        await ensure_staff_seeded(session, settings)

        existing = await session.execute(
            select(PairingCode).where(PairingCode.active.is_(True))
        )
        if existing.scalar_one_or_none() is None:
            # Prefer a stable demo code if free; else random.
            preferred = "7Q4K-9XPL"
            taken = await session.execute(
                select(PairingCode).where(PairingCode.code == preferred)
            )
            if taken.scalar_one_or_none() is None:
                now = datetime.now(UTC)
                session.add(
                    PairingCode(
                        code=preferred,
                        created_at=now,
                        expires_at=now + timedelta(hours=24),
                        active=True,
                    )
                )
            else:
                await create_pairing_code(session)
            logger.info("pairing_code_seeded")

        # Sync state defaults
        for key, value in (
            ("link_mode", settings.link_mode),
            ("updates_cursor", ""),
            ("last_sync_at", None),
            ("last_link_ok_at", None),
        ):
            row = await session.execute(select(SyncState).where(SyncState.key == key))
            if row.scalar_one_or_none() is None:
                session.add(SyncState(key=key, value=value))

        # Historical near-misses (skip if already seeded by client_id prefix)
        for i, nm in enumerate(_HISTORICAL_NEAR_MISSES):
            client_id = f"seed-nm-{i+1:02d}"
            found = await session.execute(
                select(NearMiss).where(NearMiss.client_id == client_id)
            )
            if found.scalar_one_or_none() is not None:
                continue
            created = datetime.now(UTC) - timedelta(days=7 - i)
            session.add(
                NearMiss(
                    record_id=uuid.uuid4(),
                    client_id=client_id,
                    reporter_ref=_REPORTER_REFS[i % len(_REPORTER_REFS)],
                    rank_group=nm["rank_group"],
                    created_at=created,
                    occurred_at=created - timedelta(minutes=20),
                    source=nm["source"],
                    original_language=nm["original_language"],
                    original_text=nm["original_text"],
                    english_text=nm["english_text"],
                    area=nm["area"],
                    area_detail=nm["area_detail"],
                    hazard_type=nm["hazard_type"],
                    ism_report_type=nm["ism_report_type"],
                    severity_level=nm["severity_level"],
                    potential_consequence=nm["potential_consequence"],
                    recurring=nm["recurring"],
                    description=nm["description"],
                    needs_clarification=False,
                    clarifying_question=None,
                    extraction={
                        "model": "seed",
                        "confidence": 0.9,
                        "status": "structured",
                        "attempts": 1,
                    },
                    state="confirmed",
                    status="open",
                    synced_to_shore=False,
                )
            )

        # ~30 check-in scores from 8 reporters across recent days
        existing_scores = await session.execute(
            select(CheckinScore).where(CheckinScore.source == "quick").limit(1)
        )
        if existing_scores.scalar_one_or_none() is None:
            today = date.today()
            n = 0
            for day_offset in range(5):
                d = today - timedelta(days=day_offset)
                for ri, rr in enumerate(_REPORTER_REFS):
                    if n >= 30:
                        break
                    # Vary who checks in so some days have n>=5
                    if day_offset == 4 and ri >= 4:
                        continue
                    session.add(
                        CheckinScore(
                            checkin_id=uuid.uuid4(),
                            reporter_ref=rr,
                            rank_group=["deck_rating", "engine_rating", "deck_officer", "catering"][
                                ri % 4
                            ],
                            date=d,
                            language="en",
                            mood=4 + (ri + day_offset) % 5,
                            fatigue=5 + (ri * 2 + day_offset) % 4,
                            workload=5 + (ri + day_offset * 2) % 4,
                            sleep_hours_reported=5.0 + (ri % 4),
                            social_connection=5 + ri % 3,
                            themes=["sleep", "workload"][0 : 1 + (ri % 2)],
                            source="quick",
                            rail_triggered=False,
                        )
                    )
                    n += 1
            logger.info("checkin_scores_seeded count=%s", n)

        # Index seed_docs into RAG tables
        seed_dir = Path(__file__).resolve().parent.parent / "seed_docs"
        if seed_dir.is_dir():
            for md in sorted(seed_dir.glob("*.md")):
                title = md.stem.replace("_", " ").title()
                found = await session.execute(select(Doc).where(Doc.title == title))
                if found.scalar_one_or_none() is not None:
                    continue
                body = md.read_text(encoding="utf-8")
                doc = Doc(doc_id=uuid.uuid4(), title=title)
                session.add(doc)
                await session.flush()
                for page, chunk in enumerate(_chunk_text(body), start=1):
                    session.add(
                        DocChunk(
                            chunk_id=uuid.uuid4(),
                            doc_id=doc.doc_id,
                            page=page,
                            text=chunk,
                            embedding=None,  # E7 embeds with EmbeddingGemma
                        )
                    )
                logger.info("doc_seeded title=%s", title)

        await session.commit()
        logger.info("seed_complete vessel_id=%s", settings.vessel_id)


def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
