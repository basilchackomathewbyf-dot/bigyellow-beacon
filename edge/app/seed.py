"""make seed — staff, pairing, near-misses (+photos), check-ins, alerts, SMS docs."""

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
from app.db import session as db_session
from app.db.models import (
    CheckinScore,
    Device,
    Doc,
    DocChunk,
    FleetAlert,
    HelpRequest,
    NearMiss,
    NearMissMedia,
    Notice,
    PairingCode,
    SyncState,
)
from app.logging import setup_logging

logger = logging.getLogger("beacon.seed")

# Minimal 1×1 JPEG (public domain bytes)
_MINI_JPEG = bytes(
    [
        0xFF,
        0xD8,
        0xFF,
        0xE0,
        0x00,
        0x10,
        0x4A,
        0x46,
        0x49,
        0x46,
        0x00,
        0x01,
        0x01,
        0x00,
        0x00,
        0x01,
        0x00,
        0x01,
        0x00,
        0x00,
        0xFF,
        0xDB,
        0x00,
        0x43,
        0x00,
        0x08,
        0x06,
        0x06,
        0x07,
        0x06,
        0x05,
        0x08,
        0x07,
        0x07,
        0x07,
        0x09,
        0x09,
        0x08,
        0x0A,
        0x0C,
        0x14,
        0x0D,
        0x0C,
        0x0B,
        0x0B,
        0x0C,
        0x19,
        0x12,
        0x13,
        0x0F,
        0x14,
        0x1D,
        0x1A,
        0x1F,
        0x1E,
        0x1D,
        0x1A,
        0x1C,
        0x1C,
        0x20,
        0x24,
        0x2E,
        0x27,
        0x20,
        0x22,
        0x2C,
        0x23,
        0x1C,
        0x1C,
        0x28,
        0x37,
        0x29,
        0x2C,
        0x30,
        0x31,
        0x34,
        0x34,
        0x34,
        0x1F,
        0x27,
        0x39,
        0x3D,
        0x38,
        0x32,
        0x3C,
        0x2E,
        0x33,
        0x34,
        0x32,
        0xFF,
        0xC0,
        0x00,
        0x0B,
        0x08,
        0x00,
        0x01,
        0x00,
        0x01,
        0x01,
        0x01,
        0x11,
        0x00,
        0xFF,
        0xC4,
        0x00,
        0x14,
        0x00,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x08,
        0xFF,
        0xC4,
        0x00,
        0x14,
        0x10,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0xFF,
        0xDA,
        0x00,
        0x08,
        0x01,
        0x01,
        0x00,
        0x00,
        0x3F,
        0x00,
        0x7F,
        0xFF,
        0xD9,
    ]
)

# Historical near-misses for VSL-DEMO01 — NOT the live crane demo record.
_HISTORICAL_NEAR_MISSES = [
    {
        "client_id": "seed-nm-01",
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
        "status": "open",
        "with_photo": False,
        "days_ago": 6,
    },
    {
        "client_id": "seed-nm-02",
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
        "status": "open",
        "with_photo": True,
        "days_ago": 2,
    },
    {
        "client_id": "seed-nm-03",
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
        "status": "action_assigned",
        "with_photo": False,
        "days_ago": 4,
        "action_text_en": "Tighten and inspect accommodation ladder rails before next port call",
        "action_owner_rank": "bosun",
    },
    {
        "client_id": "seed-nm-04",
        "area": "pump_room",
        "area_detail": "lower level",
        "hazard_type": "enclosed_space_atmosphere",
        "ism_report_type": "hazardous_situation",
        "severity_level": "critical",
        "potential_consequence": "fatality",
        "recurring": False,
        "original_language": "en",
        "original_text": "Gas meter alarmed at pump room entrance before entry; team stood down.",
        "english_text": "Gas meter alarmed at pump room entrance before entry; team stood down.",
        "description": "Atmosphere alarm at pump room entrance — entry aborted.",
        "rank_group": "engine_officer",
        "source": "text",
        "status": "open",
        "with_photo": True,
        "days_ago": 1,
    },
    {
        "client_id": "seed-nm-05",
        "area": "galley",
        "area_detail": None,
        "hazard_type": "fire_electrical",
        "ism_report_type": "near_miss",
        "severity_level": "high",
        "potential_consequence": "serious_injury",
        "recurring": False,
        "original_language": "en",
        "original_text": "Frayed cable on galley mixer smoked briefly; power isolated.",
        "english_text": "Frayed cable on galley mixer smoked briefly; power isolated.",
        "description": "Frayed electrical cable on galley mixer caused smoke.",
        "rank_group": "catering",
        "source": "photo",
        "status": "open",
        "with_photo": True,
        "days_ago": 0,
    },
]

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
    media_root = settings.data_dir / "media"
    media_root.mkdir(parents=True, exist_ok=True)

    db_session.init_engine(settings.database_url)
    assert db_session.async_session_factory is not None

    async with db_session.async_session_factory() as session:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        await ensure_staff_seeded(session, settings)

        existing = await session.execute(
            select(PairingCode).where(PairingCode.active.is_(True))
        )
        if existing.scalar_one_or_none() is None:
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

        for key, value in (
            ("link_mode", settings.link_mode),
            ("updates_cursor", ""),
            ("last_sync_at", None),
            ("last_link_ok_at", None),
        ):
            row = await session.execute(select(SyncState).where(SyncState.key == key))
            if row.scalar_one_or_none() is None:
                session.add(SyncState(key=key, value=value))

        # Seed a few paired devices (languages for notice hooks)
        for i, (rr, lang, rank) in enumerate(
            [
                (_REPORTER_REFS[0], "hi", "deck_rating"),
                (_REPORTER_REFS[1], "tl", "engine_rating"),
                (_REPORTER_REFS[2], "en", "deck_officer"),
            ]
        ):
            found = await session.execute(select(Device).where(Device.reporter_ref == rr))
            if found.scalar_one_or_none() is None:
                session.add(
                    Device(
                        reporter_ref=rr,
                        rank_group=rank,
                        language=lang,
                        device_label=f"seed-device-{i+1}",
                        paired_at=datetime.now(UTC),
                        revoked=False,
                    )
                )

        for i, nm in enumerate(_HISTORICAL_NEAR_MISSES):
            client_id = nm["client_id"]
            found = await session.execute(
                select(NearMiss).where(NearMiss.client_id == client_id)
            )
            if found.scalar_one_or_none() is not None:
                continue
            created = datetime.now(UTC) - timedelta(days=int(nm["days_ago"]))
            record_id = uuid.uuid4()
            row = NearMiss(
                record_id=record_id,
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
                status=nm["status"],
                action_text_en=nm.get("action_text_en"),
                action_owner_rank=nm.get("action_owner_rank"),
                synced_to_shore=False,
                embedding=None,
            )
            session.add(row)
            await session.flush()

            if nm.get("with_photo"):
                media_id = uuid.uuid4()
                dest_dir = media_root / str(record_id)
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f"{media_id}.jpg"
                dest.write_bytes(_MINI_JPEG)
                session.add(
                    NearMissMedia(
                        media_id=media_id,
                        record_id=record_id,
                        kind="photo",
                        path=str(dest.resolve()),
                        uploaded_to_shore=False,
                    )
                )

        # Check-in scores (~30 from 8 reporters)
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

        # Fleet alert (unread)
        fa = await session.execute(select(FleetAlert).limit(1))
        if fa.scalar_one_or_none() is None:
            session.add(
                FleetAlert(
                    alert_id=uuid.uuid4(),
                    cluster_id="CLU-CRANE-HYD-001",
                    title="Fleet pattern: crane hydraulic leak / slip",
                    body_en=(
                        "Sister vessels report recurring hydraulic oil leaks near crane pedestals. "
                        "Linked to accident case SYN-ACC-001. Inspect drip trays and hose fittings."
                    ),
                    severity="high",
                    linked_cases=["SYN-ACC-001"],
                    received_at=datetime.now(UTC) - timedelta(hours=6),
                    read_at=None,
                )
            )
            logger.info("fleet_alert_seeded")

        # Medical help request (open) — rank_group via device reporter_ref
        med = await session.execute(
            select(HelpRequest).where(HelpRequest.category == "medical").limit(1)
        )
        if med.scalar_one_or_none() is None:
            session.add(
                HelpRequest(
                    escalation_id=uuid.uuid4(),
                    reporter_ref=_REPORTER_REFS[0],
                    category="medical",
                    consent_to_contact=True,
                    contact_channel="ship_medic",
                    created_at=datetime.now(UTC) - timedelta(hours=2),
                    context_summary=None,  # privacy: only if consented; seed keeps null
                    status="open",
                )
            )
            logger.info("medical_alert_seeded")

        # Sample ship notice
        notice_q = await session.execute(select(Notice).limit(1))
        if notice_q.scalar_one_or_none() is None:
            session.add(
                Notice(
                    notice_id=uuid.uuid4(),
                    created_by_role="master",
                    title_en="Caution near crane 1",
                    body_en="Hydraulic oil on deck reported. Use drip trays and cordon the area.",
                    priority="urgent",
                    created_at=datetime.now(UTC) - timedelta(hours=12),
                    source="ship",
                )
            )

        # RAG docs
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
                            embedding=None,
                        )
                    )
                logger.info("doc_seeded title=%s", title)

        await session.commit()
        logger.info("seed_complete vessel_id=%s", settings.vessel_id)


def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
