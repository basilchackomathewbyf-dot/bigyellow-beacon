"""Unit tests for faster-whisper ASR wrapper (fallback behaviour)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.asr import (
    FALLBACK_TRANSCRIPT,
    WhisperTranscriber,
    is_known_hallucination,
    segments_are_non_speech,
    transcript_is_empty,
)


class _FakeSegment:
    def __init__(self, text: str, no_speech_prob: float):
        self.text = text
        self.no_speech_prob = no_speech_prob


class _FakeModel:
    def __init__(self, segments, exc: Exception | None = None):
        self._segments = segments
        self._exc = exc

    def transcribe(self, path, beam_size=5, vad_filter=False):
        if self._exc is not None:
            raise self._exc
        info = SimpleNamespace(language="en")
        return iter(self._segments), info


@pytest.fixture
def transcriber(monkeypatch):
    t = WhisperTranscriber(model_size="tiny", device="cpu", compute_type="int8")
    # Avoid real model download/load
    monkeypatch.setattr(t, "_load_whisper", lambda: None)
    return t


def test_is_known_hallucination():
    assert is_known_hallucination("Thanks for watching")
    assert is_known_hallucination("  thank you for watching! ")
    assert not is_known_hallucination("Oil mist near generator")


def test_segments_are_non_speech():
    assert segments_are_non_speech([])
    assert segments_are_non_speech([
        _FakeSegment("a", 0.9),
        _FakeSegment("b", 0.7),
    ])
    assert not segments_are_non_speech([
        _FakeSegment("hello", 0.1),
        _FakeSegment("world", 0.9),
    ])


def test_transcript_is_empty_helpers():
    assert transcript_is_empty("")
    assert transcript_is_empty("Thanks for watching")
    assert transcript_is_empty("noise", [_FakeSegment("noise", 0.95)])
    assert not transcript_is_empty("Oil leak", [_FakeSegment("Oil leak", 0.1)])


def test_empty_bytes_returns_fallback(transcriber):
    result = transcriber.transcribe_bytes(b"", filename="voice.webm")
    assert result.asr_fallback_used is True
    assert result.text == FALLBACK_TRANSCRIPT


def test_empty_text_returns_fallback(transcriber, monkeypatch):
    fake = _FakeModel([])
    monkeypatch.setattr(type(transcriber), "model", property(lambda self: fake))
    # property on instance: set _model directly
    transcriber._model = fake
    result = transcriber.transcribe_bytes(b"RIFF....fake", filename="voice.wav")
    assert result.asr_fallback_used is True
    assert result.text == FALLBACK_TRANSCRIPT


def test_high_no_speech_prob_returns_fallback(transcriber):
    fake = _FakeModel([
        _FakeSegment(" hum ", 0.85),
        _FakeSegment(" hiss ", 0.92),
    ])
    transcriber._model = fake
    result = transcriber.transcribe_bytes(b"\x00\x01audio", filename="voice.webm")
    assert result.asr_fallback_used is True
    assert result.text == FALLBACK_TRANSCRIPT


def test_hallucination_returns_fallback(transcriber):
    fake = _FakeModel([_FakeSegment("Thanks for watching", 0.05)])
    transcriber._model = fake
    result = transcriber.transcribe_bytes(b"\x00\x01audio", filename="voice.webm")
    assert result.asr_fallback_used is True
    assert result.text == FALLBACK_TRANSCRIPT


def test_exception_returns_fallback(transcriber):
    fake = _FakeModel([], exc=RuntimeError("cuda / av.open failed"))
    transcriber._model = fake
    result = transcriber.transcribe_bytes(b"\x00\x01audio", filename="voice.webm")
    assert result.asr_fallback_used is True
    assert result.text == FALLBACK_TRANSCRIPT


def test_real_speech_not_fallback(transcriber):
    fake = _FakeModel([
        _FakeSegment("Oil mist near aux generator", 0.05),
    ])
    transcriber._model = fake
    result = transcriber.transcribe_bytes(b"\x00\x01audio", filename="voice.webm")
    assert result.asr_fallback_used is False
    assert "Oil mist" in result.text
