"""Wellbeing aggregates — k-anonymity lives ONLY here."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import CheckinScore


def _suppress(n: int, k: int) -> bool:
    return n < k


def _avgs(rows: list[CheckinScore]) -> tuple[float | None, float | None, float | None]:
    if not rows:
        return None, None, None
    mood = sum(r.mood for r in rows) / len(rows)
    fatigue = sum(r.fatigue for r in rows) / len(rows)
    workload = sum(r.workload for r in rows) / len(rows)
    return round(mood, 1), round(fatigue, 1), round(workload, 1)


async def summary(session: AsyncSession, *, days: int = 14) -> dict[str, Any]:
    """Ship wellbeing summary with k-anon suppression."""
    k = get_settings().k_anon
    today = date.today()
    start = today - timedelta(days=days - 1)

    result = await session.execute(
        select(CheckinScore).where(CheckinScore.date >= start, CheckinScore.date <= today)
    )
    scores = list(result.scalars().all())

    by_date: dict[date, list[CheckinScore]] = {}
    by_rank: dict[str, list[CheckinScore]] = {}
    for s in scores:
        by_date.setdefault(s.date, []).append(s)
        by_rank.setdefault(s.rank_group, []).append(s)

    daily = []
    for offset in range(days):
        d = today - timedelta(days=offset)
        rows = by_date.get(d, [])
        # distinct reporters for k-anon
        n = len({r.reporter_ref for r in rows})
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

    by_rank_group = []
    for rank_group, rows in sorted(by_rank.items()):
        n = len({r.reporter_ref for r in rows})
        suppressed = _suppress(n, k)
        mood_avg, fatigue_avg, workload_avg = (None, None, None) if suppressed else _avgs(rows)
        by_rank_group.append(
            {
                "rank_group": rank_group,
                "n": n,
                "mood_avg": mood_avg,
                "fatigue_avg": fatigue_avg,
                "workload_avg": workload_avg,
                "suppressed": suppressed,
            }
        )

    # Themes only over windows (days) with n ≥ k
    theme_counts: dict[str, int] = {}
    for d, rows in by_date.items():
        n = len({r.reporter_ref for r in rows})
        if n < k:
            continue
        for r in rows:
            for theme in r.themes or []:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
    themes = [
        {"theme": t, "count": c}
        for t, c in sorted(theme_counts.items(), key=lambda x: (-x[1], x[0]))
    ]

    return {
        "k_threshold": k,
        "daily": daily,
        "by_rank_group": by_rank_group,
        "themes": themes,
    }


async def today_snapshot(session: AsyncSession) -> dict[str, Any]:
    """Compact wellbeing block for /ship/overview."""
    k = get_settings().k_anon
    today = date.today()
    yesterday = today - timedelta(days=1)

    result = await session.execute(select(CheckinScore).where(CheckinScore.date == today))
    today_rows = list(result.scalars().all())
    n = len({r.reporter_ref for r in today_rows})
    k_ok = n >= k

    mood_avg = fatigue_avg = workload_avg = None
    trend = "insufficient_data"
    if k_ok:
        mood_avg, fatigue_avg, workload_avg = _avgs(today_rows)
        y_result = await session.execute(
            select(CheckinScore).where(CheckinScore.date == yesterday)
        )
        y_rows = list(y_result.scalars().all())
        y_n = len({r.reporter_ref for r in y_rows})
        if y_n >= k:
            y_mood, _, _ = _avgs(y_rows)
            assert mood_avg is not None and y_mood is not None
            delta = mood_avg - y_mood
            if delta > 0.3:
                trend = "improving"
            elif delta < -0.3:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

    return {
        "k_ok": k_ok,
        "n": n,
        "mood_avg": mood_avg,
        "fatigue_avg": fatigue_avg,
        "workload_avg": workload_avg,
        "trend": trend,
    }


async def checkins_today_count(session: AsyncSession) -> int:
    today = date.today()
    result = await session.execute(
        select(func.count()).select_from(CheckinScore).where(CheckinScore.date == today)
    )
    return int(result.scalar_one())
