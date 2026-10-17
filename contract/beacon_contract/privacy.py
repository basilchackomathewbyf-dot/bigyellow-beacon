"""Privacy helpers shared by edge and shore. The k-anonymity threshold lives here only."""
from __future__ import annotations

import re
from collections.abc import Iterable

from .enums import RankBand

K_ANON = 5
SCRUB_TOKEN = "[crew]"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")
_ID_LIKE = re.compile(r"\b[A-Z]{1,3}\d{6,9}\b")  # passport / CDC / seaman's book style


def k_anon_ok(n: int) -> bool:
    return n >= K_ANON


def collapse_rank_band(band: RankBand, band_size_on_vessel: int) -> RankBand:
    """Send the real band only when at least K_ANON people share it on the vessel."""
    return band if band_size_on_vessel >= K_ANON else RankBand.CREW


def scrub_text(text: str | None, roster_names: Iterable[str] = ()) -> str | None:
    """Replace roster names, emails, phone numbers and ID-like strings with [crew].

    Run on every free-text field before it is written to the outbox.
    """
    if not text:
        return text
    out = _EMAIL.sub(SCRUB_TOKEN, text)
    out = _PHONE.sub(SCRUB_TOKEN, out)
    out = _ID_LIKE.sub(SCRUB_TOKEN, out)
    names: set[str] = set()
    for full in roster_names:
        full = full.strip()
        if not full:
            continue
        names.add(full)
        names.update(p for p in re.split(r"[\s.]+", full) if len(p) >= 3)
    for name in sorted(names, key=len, reverse=True):
        out = re.sub(rf"(?<!\w){re.escape(name)}(?!\w)", SCRUB_TOKEN, out, flags=re.IGNORECASE)
    return out


# Keys that must never appear anywhere in a SyncDelta (checked recursively by the contract).
FORBIDDEN_SYNC_KEYS: frozenset[str] = frozenset({
    "reporter_crew_id", "crew_id", "display_name", "name", "pin", "pin_hash", "device_id",
    "device_token", "transcript", "transcript_original", "audio", "audio_path",
    "checkin_text", "email", "phone",
})
