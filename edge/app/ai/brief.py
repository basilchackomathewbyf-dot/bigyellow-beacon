"""Brief generation stub — model not wired yet (E2)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.ai.errors import ModelNotReady


async def generate_brief(context: dict[str, Any]) -> dict[str, Any]:
    """Call Gemma for a master brief. E4: always unavailable."""
    raise ModelNotReady("model server not ready (E4 stub)")


def build_fallback_brief(context: dict[str, Any]) -> dict[str, Any]:
    """Deterministic brief from aggregates — valid against master_brief.schema.json."""
    vessel_id = context["vessel_id"]
    brief_date = context.get("brief_date") or date.today().isoformat()
    wellbeing = context.get("wellbeing") or {}
    open_hazards = context.get("open_hazards") or []
    evidence_refs = context.get("evidence_refs") or ["none"]

    k_ok = bool(wellbeing.get("k_ok"))
    n = wellbeing.get("n") or 0
    mood = wellbeing.get("mood_avg")
    fatigue = wellbeing.get("fatigue_avg")
    trend = wellbeing.get("trend") or "insufficient_data"

    if not k_ok:
        crew_trend = {
            "direction": "insufficient_data",
            "summary": f"Fewer than 5 check-ins today (n={n}); trend withheld (k-anonymity).",
            "k_anonymity_ok": False,
        }
        rest_level = "medium"
        rest_summary = "Insufficient check-in volume to assess rest risk."
    else:
        direction = trend if trend in ("improving", "stable", "declining") else "stable"
        crew_trend = {
            "direction": direction,
            "summary": (
                f"Today n={n}: mood {mood:.1f}, fatigue {fatigue:.1f} (0–10). "
                f"Trend: {direction}."
            )[:240],
            "k_anonymity_ok": True,
        }
        rest_level = "high" if (fatigue or 0) >= 7 else ("medium" if (fatigue or 0) >= 5 else "low")
        rest_summary = (
            f"Fatigue average {fatigue:.1f}/10 across {n} check-ins; "
            f"rest risk assessed as {rest_level}."
        )[:240]

    hazard_items = []
    for h in open_hazards[:5]:
        hazard_items.append(
            {
                "hazard_type": h["hazard_type"],
                "area": h["area"],
                "count_7d": int(h["count_7d"]),
                "fleet_cluster_id": h.get("fleet_cluster_id"),
                "linked_cases": h.get("linked_cases") or [],
            }
        )

    if hazard_items:
        top = hazard_items[0]
        action = {
            "action": f"Review and close open {top['hazard_type']} in {top['area']}"[:200],
            "why": (
                f"{top['count_7d']} confirmed report(s) in 7 days for this area/hazard; "
                "assign corrective action before next watch."
            )[:300],
            "evidence_refs": evidence_refs[:10] if evidence_refs else ["none"],
        }
    else:
        action = {
            "action": "No open high/critical hazards — continue routine safety rounds",
            "why": "Deterministic fallback: no open high or critical confirmed near-misses.",
            "evidence_refs": evidence_refs if evidence_refs != ["none"] else ["none"],
        }

    return {
        "vessel_id": vessel_id,
        "brief_date": brief_date,
        "rest_compliance": {"risk_level": rest_level, "summary": rest_summary},
        "crew_trend": crew_trend,
        "open_hazards": hazard_items,
        "recommended_action": action,
        "provenance": {
            "model": "deterministic-fallback",
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "inputs": [
                "checkin_scores",
                "near_misses",
                "fleet_alerts",
            ],
        },
    }
