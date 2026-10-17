"""Seed vessel + roster from ROSTER_FILE. Run via `make seed`."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db.models import Crew, SyncState, TicketSeq, Vessel
from app.db.session import get_engine, init_engine

logger = logging.getLogger("beacon.edge.seed")


async def seed_roster(session) -> None:
    settings = get_settings()
    roster_path = Path(settings.roster_file)
    if not roster_path.is_file():
        raise FileNotFoundError(f"Roster file not found: {roster_path}")

    data = json.loads(roster_path.read_text(encoding="utf-8"))
    vessel_id = data.get("vessel_id") or settings.vessel_id

    vessel = await session.get(Vessel, vessel_id)
    if vessel is None:
        session.add(
            Vessel(
                id=vessel_id,
                name=settings.vessel_name,
                type="bulk",
                fleet_group="demo",
                vessel_secret=settings.vessel_secret,
            )
        )
    else:
        vessel.name = settings.vessel_name
        vessel.vessel_secret = settings.vessel_secret

    seq = await session.get(TicketSeq, vessel_id)
    if seq is None:
        session.add(TicketSeq(vessel_id=vessel_id, last_seq=0))

    sync = await session.get(SyncState, vessel_id)
    if sync is None:
        session.add(
            SyncState(
                vessel_id=vessel_id,
                link_status="down",
                link_override=settings.link_override,
            )
        )

    for member in data["crew"]:
        crew_id = member["crew_id"]
        existing = await session.get(Crew, crew_id)
        if existing is None:
            session.add(
                Crew(
                    id=crew_id,
                    vessel_id=vessel_id,
                    display_name=member["display_name"],
                    rank=member["rank"],
                    rank_band=member["rank_band"],
                    language=member.get("language", "en"),
                    is_master=bool(member.get("is_master", False)),
                    active=True,
                    pin_hash=None,  # set at pairing
                )
            )
        else:
            existing.display_name = member["display_name"]
            existing.rank = member["rank"]
            existing.rank_band = member["rank_band"]
            existing.language = member.get("language", "en")
            existing.is_master = bool(member.get("is_master", False))
            existing.active = True
            existing.vessel_id = vessel_id

    await session.flush()
    count = len((await session.execute(select(Crew))).scalars().all())
    logger.info("seeded vessel=%s crew=%d", vessel_id, count)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    init_engine(settings.database_url)
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with factory() as session:
        await seed_roster(session)
        await session.commit()
    print(f"Seeded roster from {settings.roster_file}")


if __name__ == "__main__":
    asyncio.run(main())
