"""Master brief — prefer shore_enriched, else edge; AI stub falls back to deterministic."""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import jsonschema
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.brief import build_fallback_brief, generate_brief
from app.ai.errors import ModelNotReady
from app.config import get_settings
from app.db.models import Brief, NearMiss
from app.services import wellbeing_service

logger = logging.getLogger("beacon.brief")


def _load_schema() -> dict[str, Any]:
    path = Path(get_settings().contracts_dir) / "schemas" / "master_brief.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_brief(payload: dict[str, Any]) -> None:
    jsonschema.validate(payload, _load_schema())


async def _hazard_context(session: AsyncSession) -> tuple[list[dict[str, Any]], list[str]]:
    since = datetime.now(UTC) - timedelta(days=7)
    result = await session.execute(
        select(NearMiss).where(
            NearMiss.state == "confirmed",
            NearMiss.status.in_(("open", "action_assigned")),
            NearMiss.severity_level.in_(("high", "critical")),
            NearMiss.created_at >= since,
        )
    )
    rows = list(result.scalars().all())
    buckets: dict[tuple[str, str], list[NearMiss]] = {}
    for r in rows:
        buckets.setdefault((r.hazard_type, r.area), []).append(r)
    open_hazards = [
        {
            "hazard_type": ht,
            "area": area,
            "count_7d": len(items),
            "fleet_cluster_id": None,
            "linked_cases": [],
        }
        for (ht, area), items in sorted(buckets.items(), key=lambda x: -len(x[1]))
    ]
    evidence = [str(r.record_id) for r in rows[:10]] or ["none"]
    return open_hazards, evidence


async def build_context(session: AsyncSession) -> dict[str, Any]:
    settings = get_settings()
    wellbeing = await wellbeing_service.today_snapshot(session)
    open_hazards, evidence_refs = await _hazard_context(session)
    return {
        "vessel_id": settings.vessel_id,
        "brief_date": date.today().isoformat(),
        "wellbeing": wellbeing,
        "open_hazards": open_hazards,
        "evidence_refs": evidence_refs,
    }


async def get_or_create_today(session: AsyncSession, *, force: bool = False) -> dict[str, Any]:
    """Return today's brief. Prefer newer shore_enriched; else edge (fallback if AI down)."""
    today = date.today()

    if not force:
        shore = await session.execute(
            select(Brief)
            .where(Brief.brief_date == today, Brief.source == "shore_enriched")
            .order_by(Brief.created_at.desc())
            .limit(1)
        )
        shore_row = shore.scalar_one_or_none()
        edge = await session.execute(
            select(Brief)
            .where(Brief.brief_date == today, Brief.source == "edge")
            .order_by(Brief.created_at.desc())
            .limit(1)
        )
        edge_row = edge.scalar_one_or_none()
        if shore_row and (edge_row is None or shore_row.created_at >= edge_row.created_at):
            return {"source": "shore_enriched", "brief": shore_row.payload}
        if edge_row is not None:
            return {"source": "edge", "brief": edge_row.payload}

    context = await build_context(session)
    try:
        payload = await generate_brief(context)
    except ModelNotReady:
        logger.info("brief_fallback reason=model_not_ready")
        payload = build_fallback_brief(context)

    validate_brief(payload)

    # Upsert edge brief for today
    existing = await session.execute(
        select(Brief).where(Brief.brief_date == today, Brief.source == "edge")
    )
    row = existing.scalar_one_or_none()
    if row is None:
        session.add(
            Brief(
                brief_date=today,
                source="edge",
                payload=payload,
                created_at=datetime.now(UTC),
            )
        )
    else:
        row.payload = payload
        row.created_at = datetime.now(UTC)
    await session.commit()
    return {"source": "edge", "brief": payload}


async def open_hazard_counts(session: AsyncSession) -> tuple[int, int]:
    """(open_hazards, high_or_critical_open) for confirmed non-closed."""
    open_n = int(
        (
            await session.execute(
                select(func.count())
                .select_from(NearMiss)
                .where(
                    NearMiss.state == "confirmed",
                    NearMiss.status.in_(("open", "action_assigned")),
                )
            )
        ).scalar_one()
    )
    high_n = int(
        (
            await session.execute(
                select(func.count())
                .select_from(NearMiss)
                .where(
                    NearMiss.state == "confirmed",
                    NearMiss.status.in_(("open", "action_assigned")),
                    NearMiss.severity_level.in_(("high", "critical")),
                )
            )
        ).scalar_one()
    )
    return open_n, high_n
