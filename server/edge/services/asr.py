"""
faster-whisper ASR wrapper for edge voice memos.

CUDA (medium/float16) preferred; falls back to small/cpu/int8.
Never raises to callers — empty / failed ASR returns FALLBACK_TRANSCRIPT.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence

logger = logging.getLogger("edge.asr")

# Defaults mirror config.py (avoid importing config at module load for unit tests).
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")

FALLBACK_TRANSCRIPT = (
    "Oil mist observed near auxiliary generator 2 turbocharger return flange during 0400 rounds."
)

# Common Whisper hallucinations when audio is silence / noise / music.
_KNOWN_HALLUCINATIONS = frozenset(
    {
        "thanks for watching",
        "thank you for watching",
        "thanks for watching!",
        "thank you for watching!",
        "subscribe",
        "please subscribe",
        "like and subscribe",
    }
)

_NO_SPEECH_PROB_THRESHOLD = 0.6


@dataclass(frozen=True)
class AsrResult:
    text: str
    asr_fallback_used: bool


def _normalize_hallucination(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_known_hallucination(text: str) -> bool:
    return _normalize_hallucination(text) in _KNOWN_HALLUCINATIONS


def segments_are_non_speech(segments: Sequence[Any]) -> bool:
    """True when every segment looks like non-speech (no_speech_prob > 0.6)."""
    if not segments:
        return True
    probs: List[float] = []
    for seg in segments:
        p = getattr(seg, "no_speech_prob", None)
        if p is None:
            return False
        probs.append(float(p))
    return bool(probs) and all(p > _NO_SPEECH_PROB_THRESHOLD for p in probs)


def transcript_is_empty(
    text: str,
    segments: Optional[Sequence[Any]] = None,
) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    if is_known_hallucination(stripped):
        return True
    if segments is not None and segments_are_non_speech(segments):
        return True
    return False


class WhisperTranscriber:
    """Lazy-loaded faster-whisper model with CUDA → CPU fallback."""

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        self.model_size = model_size or WHISPER_MODEL_SIZE
        self.device = (device or WHISPER_DEVICE or "cuda").lower()
        self.compute_type = compute_type or WHISPER_COMPUTE_TYPE
        self._model = None

    def _load_whisper(self):
        from faster_whisper import WhisperModel

        if self.device == "cuda":
            try:
                return WhisperModel(
                    self.model_size,
                    device="cuda",
                    compute_type=self.compute_type,
                )
            except Exception as e:
                logger.warning(
                    "Whisper %s on cuda/%s failed (%s); falling back to small/cpu/int8",
                    self.model_size,
                    self.compute_type,
                    e,
                )
                return WhisperModel("small", device="cpu", compute_type="int8")

        if self.device != "cpu":
            logger.warning(
                "Unknown WHISPER_DEVICE=%s; falling back to small/cpu/int8",
                self.device,
            )
            return WhisperModel("small", device="cpu", compute_type="int8")

        try:
            return WhisperModel(self.model_size, device="cpu", compute_type="int8")
        except Exception as e:
            logger.warning(
                "Whisper %s on cpu/int8 failed (%s); using small/cpu/int8",
                self.model_size,
                e,
            )
            return WhisperModel("small", device="cpu", compute_type="int8")

    @property
    def model(self):
        if self._model is None:
            self._model = self._load_whisper()
        return self._model

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
    ) -> AsrResult:
        import time as _time

        if not audio_bytes:
            logger.warning(
                "ASR failed or empty, using FALLBACK_TRANSCRIPT reason=no_bytes filename=%s",
                filename,
                exc_info=True,
            )
            return AsrResult(text=FALLBACK_TRANSCRIPT, asr_fallback_used=True)

        suffix = Path(filename).suffix or ".webm"
        temp_path = Path(f"/tmp/beacon_asr_{os.getpid()}{suffix}")
        t0 = _time.perf_counter()
        try:
            temp_path.write_bytes(audio_bytes)
            segments_iter, _info = self.model.transcribe(
                str(temp_path),
                beam_size=5,
                vad_filter=True,
            )
            segments = list(segments_iter)
            transcript = " ".join((seg.text or "").strip() for seg in segments).strip()
            ms = int((_time.perf_counter() - t0) * 1000)

            if not (transcript or "").strip():
                logger.warning(
                    "ASR failed or empty, using FALLBACK_TRANSCRIPT reason=empty_text "
                    "filename=%s bytes=%s ms=%s",
                    filename,
                    len(audio_bytes),
                    ms,
                    exc_info=True,
                )
                return AsrResult(text=FALLBACK_TRANSCRIPT, asr_fallback_used=True)
            if is_known_hallucination(transcript):
                logger.warning(
                    "ASR failed or empty, using FALLBACK_TRANSCRIPT reason=hallucination "
                    "filename=%s bytes=%s ms=%s transcript_len=%s",
                    filename,
                    len(audio_bytes),
                    ms,
                    len(transcript),
                    exc_info=True,
                )
                return AsrResult(text=FALLBACK_TRANSCRIPT, asr_fallback_used=True)
            if segments_are_non_speech(segments):
                logger.warning(
                    "ASR failed or empty, using FALLBACK_TRANSCRIPT reason=no_speech "
                    "filename=%s bytes=%s ms=%s",
                    filename,
                    len(audio_bytes),
                    ms,
                    exc_info=True,
                )
                return AsrResult(text=FALLBACK_TRANSCRIPT, asr_fallback_used=True)

            logger.info(
                "ASR ok filename=%s bytes=%s ms=%s transcript_len=%s device=%s model=%s",
                filename,
                len(audio_bytes),
                ms,
                len(transcript),
                self.device,
                self.model_size,
            )
            return AsrResult(text=transcript, asr_fallback_used=False)
        except Exception:
            ms = int((_time.perf_counter() - t0) * 1000)
            logger.warning(
                "ASR failed or empty, using FALLBACK_TRANSCRIPT reason=exception "
                "filename=%s bytes=%s ms=%s",
                filename,
                len(audio_bytes),
                ms,
                exc_info=True,
            )
            return AsrResult(text=FALLBACK_TRANSCRIPT, asr_fallback_used=True)
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass


# Process-wide singleton used by AIGateway / routes.
_default_transcriber: Optional[WhisperTranscriber] = None


def get_transcriber() -> WhisperTranscriber:
    global _default_transcriber
    if _default_transcriber is None:
        _default_transcriber = WhisperTranscriber()
    return _default_transcriber


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> AsrResult:
    """Async-friendly wrapper (Whisper itself is sync/CPU-bound)."""
    return get_transcriber().transcribe_bytes(audio_bytes, filename=filename)
