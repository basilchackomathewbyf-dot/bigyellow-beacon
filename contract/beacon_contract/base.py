from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Base for every payload. Unknown fields are rejected so drift is caught early."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def uuid7() -> uuid.UUID:
    """RFC 9562 UUIDv7: 48-bit unix ms timestamp, version 7, variant 10, random bits."""
    ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits
    value = (
        (ms & ((1 << 48) - 1)) << 80
        | 0x7 << 76
        | ((rand >> 68) & 0xFFF) << 64
        | 0b10 << 62
        | (rand & ((1 << 62) - 1))
    )
    return uuid.UUID(int=value)


def new_id() -> str:
    return str(uuid7())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ticket_no(vessel_code: str, seq: int) -> str:
    """BCN-<vessel code>-<4-digit seq>, e.g. BCN-0007-0012. Generated on the edge."""
    return f"BCN-{vessel_code}-{seq:04d}"


def _require_en(v: dict[str, str]) -> dict[str, str]:
    if "en" not in v or not v["en"].strip():
        raise ValueError("localized text must include a non-empty 'en' entry")
    return v


LocalizedText = Annotated[dict[str, str], AfterValidator(_require_en)]
"""Text keyed by language code; 'en' is always present."""

Id = Annotated[str, Field(min_length=1, max_length=64)]
Score1to5 = Annotated[int, Field(ge=1, le=5)]
ShortText = Annotated[str, Field(min_length=1, max_length=200)]
LongText = Annotated[str, Field(min_length=1, max_length=4000)]
