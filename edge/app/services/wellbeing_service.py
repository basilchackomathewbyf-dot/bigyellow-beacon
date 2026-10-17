"""Wellbeing aggregates — k-anonymity lives ONLY here."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Checkin, Crew


def _suppress(n: int, k: int) -> bool:
    return n < k


def _avgs(rows: list[Checkin]) -> tuple[float | None, float | None, float | None]:
    if not rows:
        return None, None, None
    mood = sum(r.mood for r in rows) / len(rows)
    fatigue = sum(r.fatigue for r in rows) / len(rows)
    workload = sum(r.workload for r in rows) / len(rows)
    return round(mood, 1), round(fatigue, 1), round(workload, 1)


async def daily_k_anon(
    session: AsyncSession,
    *,
    ship_date: date | None = None,
) -> dict[str, Any]:
    """Single-day aggregate with k-anon suppression (used by tests + brief)."""
    k = get_settings().k_anon
    d = ship_date or date.today()
    result = await session.execute(select(Checkin).where(Checkin.ship_date == d))
    rows = list(result.scalars().all())
    n = len({r.crew_id for r in rows})
    suppressed = _suppress(n, k)
    mood_avg, fatigue_avg, workload_avg = (None, None, None) if suppressed else _avgs(rows)
    return {
        "date": d.isoformat(),
        "k_threshold": k,
        "n": n,
        "mood_avg": mood_avg,
        "fatigue_avg": fatigue_avg,
        "workload_avg": workload_avg,
        "suppressed": suppressed,
    }


async def summary(session: AsyncSession, *, days: int = 14) -> dict[str, Any]:
    """Ship wellbeing summary with k-anon suppression."""
    k = get_settings().k_anon
    today = date.today()
    start = today - timedelta(days=days - 1)

    result = await session.execute(
        select(Checkin).where(Checkin.ship_date >= start, Checkin.ship_date <= today)
    )
    scores = list(result.scalars().all())

    crew_ids = {s.crew_id for s in scores}
    bands: dict[str, str] = {}
    if crew_ids:
        crew_rows = (
            await session.execute(select(Crew).where(Crew.id.in_(crew_ids)))
        ).scalars().all()
        bands = {c.id: c.rank_band for c in crew_rows}

    by_date: dict[date, list[Checkin]] = {}
    by_band: dict[str, list[Checkin]] = {}
    for s in scores:
        by_date.setdefault(s.ship_date, []).append(s)
        by_band.setdefault(bands.get(s.crew_id, "crew"), []).append(s)

    daily = []
    for offset in range(days):
        d = today - timedelta(days=offset)
        rows = by_date.get(d, [])
        n = len({r.crew_id for r in rows})
        suppressed = _suppress(n, k)
        mood_avg, fatigue_avg, workload_avg = (None, None, None) if suppressed else _avgs(rows)
        daily.append(
            {
                "date": d.isoformat(),
                "n": n,
                "mood_avg": mood_avg,
                "fatigue_avg": fatigue_avg,
                "workload_avg": workload_avg,
                "suppressed": suppressed,
            }
        )

    by_rank_band = []
    for rank_band, rows in sorted(by_band.items()):
        n = len({r.crew_id for r in rows})
        suppressed = _suppress(n, k)
        mood_avg, fatigue_avg, workload_avg = (None, None, None) if suppressed else _avgs(rows)
        by_rank_band.append(
            {
                "rank_band": rank_band,
                "n": n,
                "mood_avg": mood_avg,
                "fatigue_avg": fatigue_avg,
                "workload_avg": workload_avg,
                "suppressed": suppressed,
            }
        )

    return {
        "k_threshold": k,
        "daily": daily,
        "by_rank_band": by_rank_band,
    }
