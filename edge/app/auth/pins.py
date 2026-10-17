"""PIN hashing (argon2id) and device lockout persisted on devices rows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.low_level import Type

from app.db.models import Device

# Explicit argon2id (default in argon2-cffi, pinned for clarity).
_ph = PasswordHasher(type=Type.ID)

MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60


def hash_pin(pin: str) -> str:
    return _ph.hash(pin)


def verify_pin(pin_hash: str, pin: str) -> bool:
    try:
        return _ph.verify(pin_hash, pin)
    except VerifyMismatchError:
        return False


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def lockout_remaining(device: Device, *, now: datetime | None = None) -> int:
    """Seconds left on lockout, or 0 if not locked.

    Clears expired lock fields on the device (caller must commit).
    """
    if device.locked_until is None:
        return 0
    t = now or _utcnow()
    until = _ensure_aware(device.locked_until)
    remaining = int((until - t).total_seconds())
    if remaining <= 0:
        device.failed_pin_attempts = 0
        device.locked_until = None
        return 0
    return remaining


def is_locked(device: Device, *, now: datetime | None = None) -> bool:
    return lockout_remaining(device, now=now) > 0


def record_failure(device: Device, *, now: datetime | None = None) -> int:
    """Record a bad PIN on the device row. Returns retry_after if locked, else 0."""
    t = now or _utcnow()
    remaining = lockout_remaining(device, now=t)
    if remaining > 0:
        return remaining
    device.failed_pin_attempts = int(device.failed_pin_attempts or 0) + 1
    if device.failed_pin_attempts >= MAX_FAILURES:
        device.locked_until = t + timedelta(seconds=LOCKOUT_SECONDS)
        return LOCKOUT_SECONDS
    return 0


def clear_failures(device: Device) -> None:
    device.failed_pin_attempts = 0
    device.locked_until = None


def expected_pin_length(*, is_master: bool) -> int:
    return 6 if is_master else 4


def validate_pin_length(pin: str, *, is_master: bool) -> bool:
    return len(pin) == expected_pin_length(is_master=is_master) and pin.isdigit()
