"""AI gateway seam — Protocol + Fake (Basil); OllamaGateway (Sumit)."""

from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from beacon_contract import fixtures
from beacon_contract.edge_api import CheckinAfter, CheckinScores, MoodEntry, MoodInsight, MorningBrief

from app.ai.types import (
    BriefContext,
    CheckinTurnResult,
    PhotoCaptions,
    StructureResult,
    Transcript,
    Turn,
)
from app.config import get_settings


def _fake_delay_s() -> float:
    # Default 1 s; tests set BEACON_AI_FAKE_DELAY=0.
    return float(os.environ.get("BEACON_AI_FAKE_DELAY", "1"))


class AIGateway(Protocol):
    async def transcribe(self, audio_path: Path, lang_hint: str | None) -> Transcript: ...

    async def caption_photos(self, photo_paths: list[Path]) -> PhotoCaptions: ...

    async def structure_report(
        self,
        text: str,
        language: str,
        captions: PhotoCaptions | None,
        location_hints: list[str],
    ) -> StructureResult: ...

    async def answer_clarification(
        self, prior: StructureResult, question: str, answer: str
    ) -> StructureResult: ...

    async def checkin_turn(self, history: list[Turn], language: str) -> CheckinTurnResult: ...

    async def checkin_after(
        self, scores: CheckinScores, tags: list[str], language: str
    ) -> CheckinAfter: ...

    async def morning_brief(self, ctx: BriefContext) -> MorningBrief: ...

    async def mood_insight(
        self, entries: list[MoodEntry], language: str
    ) -> MoodInsight | None: ...

    async def translate(self, text: str, src: str, tgt: str) -> str: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


def _structure_from_fixture(resp) -> StructureResult:
    return StructureResult(
        fields=resp.fields,
        clarifying_question=resp.clarifying_question,
        confidence=resp.confidence,
        original_language=str(resp.original_language),
        prompt_version=resp.prompt_version,
        model=resp.model,
        transcript_original=resp.transcript_original,
    )


class FakeAIGateway:
    """Returns beacon_contract.fixtures with a 1 s delay (demo / tests)."""

    async def _delay(self) -> None:
        await asyncio.sleep(_fake_delay_s())

    async def transcribe(self, audio_path: Path, lang_hint: str | None) -> Transcript:
        await self._delay()
        return Transcript(text=fixtures.HINDI_REPORT, language=lang_hint or "hi", avg_logprob=-0.4)

    async def caption_photos(self, photo_paths: list[Path]) -> PhotoCaptions:
        await self._delay()
        return PhotoCaptions(
            caption="Deck area near a ship crane with a dark patch on the plating",
            visible_hazards=["slip_trip_fall", "machinery_hydraulic"],
        )

    async def structure_report(
        self,
        text: str,
        language: str,
        captions: PhotoCaptions | None,
        location_hints: list[str],
    ) -> StructureResult:
        await self._delay()
        return _structure_from_fixture(fixtures.structure_response())

    async def answer_clarification(
        self, prior: StructureResult, question: str, answer: str
    ) -> StructureResult:
        await self._delay()
        return _structure_from_fixture(fixtures.structure_after_answer())

    async def checkin_turn(self, history: list[Turn], language: str) -> CheckinTurnResult:
        await self._delay()
        return CheckinTurnResult(
            reply="Thanks for sharing. How is your workload today?",
            done=False,
            scores=None,
        )

    async def checkin_after(
        self, scores: CheckinScores, tags: list[str], language: str
    ) -> CheckinAfter:
        await self._delay()
        return CheckinAfter(
            supportive_line="Rest when you can — you are doing important work.",
            tip="Drink water and stretch before the next watch.",
        )

    async def morning_brief(self, ctx: BriefContext) -> MorningBrief:
        await self._delay()
        return fixtures.morning_brief()

    async def mood_insight(
        self, entries: list[MoodEntry], language: str
    ) -> MoodInsight | None:
        await self._delay()
        return None

    async def translate(self, text: str, src: str, tgt: str) -> str:
        await self._delay()
        return text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        await self._delay()
        # Deterministic stub vectors (no real similarity matches).
        return [[0.01 * (i + 1)] * 768 for i, _ in enumerate(texts)]


class OllamaGateway:
    """Sumit implements against Ollama + faster-whisper (milestone A2)."""

    async def transcribe(self, audio_path: Path, lang_hint: str | None) -> Transcript:
        raise NotImplementedError("OllamaGateway.transcribe — Sumit / A2")

    async def caption_photos(self, photo_paths: list[Path]) -> PhotoCaptions:
        raise NotImplementedError("OllamaGateway.caption_photos — Sumit / A2")

    async def structure_report(
        self,
        text: str,
        language: str,
        captions: PhotoCaptions | None,
        location_hints: list[str],
    ) -> StructureResult:
        raise NotImplementedError("OllamaGateway.structure_report — Sumit / A2")

    async def answer_clarification(
        self, prior: StructureResult, question: str, answer: str
    ) -> StructureResult:
        raise NotImplementedError("OllamaGateway.answer_clarification — Sumit / A2")

    async def checkin_turn(self, history: list[Turn], language: str) -> CheckinTurnResult:
        raise NotImplementedError("OllamaGateway.checkin_turn — Sumit / A7")

    async def checkin_after(
        self, scores: CheckinScores, tags: list[str], language: str
    ) -> CheckinAfter:
        raise NotImplementedError("OllamaGateway.checkin_after — Sumit / A7")

    async def morning_brief(self, ctx: BriefContext) -> MorningBrief:
        raise NotImplementedError("OllamaGateway.morning_brief — Sumit / A7")

    async def mood_insight(
        self, entries: list[MoodEntry], language: str
    ) -> MoodInsight | None:
        raise NotImplementedError("OllamaGateway.mood_insight — Sumit / A8")

    async def translate(self, text: str, src: str, tgt: str) -> str:
        raise NotImplementedError("OllamaGateway.translate — Sumit / A2")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("OllamaGateway.embed — Sumit / A2")


@lru_cache
def get_gateway() -> AIGateway:
    settings = get_settings()
    if settings.ai == "ollama":
        return OllamaGateway()  # type: ignore[return-value]
    return FakeAIGateway()  # type: ignore[return-value]


def reset_gateway_cache() -> None:
    """Test helper."""
    get_gateway.cache_clear()
