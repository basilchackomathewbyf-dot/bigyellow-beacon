"""
Deterministic safety rails for BigYellow Beacon.

Runs BEFORE the model sees crew input and AFTER the model responds.
If a rail fires, the model output is discarded and a FIXED response is shown.

IMPORTANT (hackathon): the phrase lists and fixed responses below are
PLACEHOLDERS written by the dev team. They must be reviewed and replaced
by BYF's clinical/psychology team before any real crew sees them.
Port this file 1:1 to Kotlin/Swift for on-device use; keep the JSON
lexicon (lexicon.json) as the single source of truth.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

LEXICON_PATH = Path(__file__).resolve().parent / "rules" / "lexicon.json"


@dataclass(frozen=True)
class RailResult:
    triggered: bool
    category: str | None = None      # crisis | harm_to_others | medical_emergency
    stage: str | None = None         # pre_model | post_model
    matched_rule: str | None = None  # rule id, for audit; never the user's text
    fixed_response: str | None = None


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", " ", text).strip()


class SafetyRails:
    def __init__(self, lexicon_path: Path = LEXICON_PATH):
        data = json.loads(lexicon_path.read_text(encoding="utf-8"))
        self.version = data["version"]
        self.responses = data["fixed_responses"]
        self.rules = [
            (r["id"], r["category"], re.compile(r["pattern"], re.IGNORECASE | re.UNICODE))
            for r in data["rules"]
        ]
        # Things the MODEL must never say (post-model check).
        self.output_rules = [
            (r["id"], re.compile(r["pattern"], re.IGNORECASE | re.UNICODE))
            for r in data["model_output_blocklist"]
        ]

    def _response(self, category: str, lang: str) -> str:
        by_lang = self.responses[category]
        return by_lang.get(lang) or by_lang["en"]

    def check_input(self, text: str, lang: str = "en") -> RailResult:
        t = _normalise(text)
        for rule_id, category, pat in self.rules:
            if pat.search(t):
                return RailResult(True, category, "pre_model", rule_id, self._response(category, lang))
        return RailResult(False)

    def check_output(self, model_text: str, crew_text: str, lang: str = "en") -> RailResult:
        # Re-check crew text (defence in depth) then the model's own words.
        pre = self.check_input(crew_text, lang)
        if pre.triggered:
            return RailResult(True, pre.category, "post_model", pre.matched_rule, pre.fixed_response)
        t = _normalise(model_text)
        for rule_id, pat in self.output_rules:
            if pat.search(t):
                return RailResult(True, "crisis", "post_model", rule_id, self._response("crisis", lang))
        return RailResult(False)


def guarded_turn(rails: SafetyRails, crew_text: str, lang: str, generate) -> tuple[str, RailResult]:
    """Wrap one model turn. `generate` is any callable(str) -> str (Gemma on device, Gemini ashore)."""
    pre = rails.check_input(crew_text, lang)
    if pre.triggered:
        return pre.fixed_response, pre          # model never called
    reply = generate(crew_text)
    post = rails.check_output(reply, crew_text, lang)
    if post.triggered:
        return post.fixed_response, post       # model reply discarded
    return reply, RailResult(False)
