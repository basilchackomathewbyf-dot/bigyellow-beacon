"""Internal AI gateway types. User-facing responses use beacon_contract models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from beacon_contract.edge_api import (
    CheckinAfter,
    CheckinScores,
    MoodEntry,
    MoodInsight,
    MorningBrief,
    StructuredFields,
)


@dataclass
class Transcript:
    text: str
    language: str
    avg_logprob: float | None = None


@dataclass
class PhotoCaptions:
    caption: str
    visible_hazards: list[str] = field(default_factory=list)


@dataclass
class StructureResult:
    fields: StructuredFields
    clarifying_question: dict[str, str] | None = None
    confidence: float = 0.0
    original_language: str = "en"
    prompt_version: str = "structure/v1"
    model: str = "unknown"
    transcript_original: str | None = None


@dataclass
class Turn:
    role: str  # user | assistant
    text: str


@dataclass
class CheckinTurnResult:
    reply: str
    done: bool
    scores: CheckinScores | None = None


@dataclass
class BriefContext:
    """Inputs for morning brief generation."""

    open_tickets: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    aggregates: list[dict[str, Any]] = field(default_factory=list)
    fleet_context: str | None = None


# Re-export contract types used in the Protocol signatures.
__all__ = [
    "BriefContext",
    "CheckinAfter",
    "CheckinScores",
    "CheckinTurnResult",
    "MoodEntry",
    "MoodInsight",
    "MorningBrief",
    "PhotoCaptions",
    "StructureResult",
    "Transcript",
    "Turn",
]
