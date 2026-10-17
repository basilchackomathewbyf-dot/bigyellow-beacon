"""Staff PIN login with argon2 hashes and lockout."""

from __future__ import annotations

import time
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import StaffUser

_ph = PasswordHasher()

MAX_FAILURES = 5
LOCKOUT_SECONDS = 300  # 5 minutes


@dataclass
class _AttemptState:
    failures: int = 0
    locked_until: float = 0.0


# In-process lockout tracker keyed by username (hackathon-scale).
_attempts: dict[str, _AttemptState] = {}


def hash_pin(pin: str) -> str:
    return _ph.hash(pin)


def verify_pin(pin_hash: str, pin: str) -> bool:
    try:
        return _ph.verify(pin_hash, pin)
    except VerifyMismatchError:
        return False


def is_locked(username: str) -> bool:
    state = _attempts.get(username)
    if state is None:
        return False
    if state.locked_until and time.monotonic() < state.locked_until:
        return True
    if state.locked_until and time.monotonic() >= state.locked_until:
        state.failures = 0
        state.locked_until = 0.0
    return False


def record_failure(username: str) -> None:
    state = _attempts.setdefault(username, _AttemptState())
    state.failures += 1
    if state.failures >= MAX_FAILURES:
        state.locked_until = time.monotonic() + LOCKOUT_SECONDS


def clear_failures(username: str) -> None:
    _attempts.pop(username, None)


def reset_lockouts() -> None:
    """Test helper."""
    _attempts.clear()


async def ensure_staff_seeded(session: AsyncSession, settings: Settings | None = None) -> None:
    """Upsert master and safety_officer from env PIN values."""
    s = settings or get_settings()
    for username, pin, role in (
        (s.master_username, s.master_pin, "master"),
        (s.so_username, s.so_pin, "safety_officer"),
    ):
        result = await session.execute(select(StaffUser).where(StaffUser.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            session.add(
                StaffUser(username=username, pin_hash=hash_pin(pin), role=role)
            )
        else:
            # Keep hash in sync if env PIN changed and verify fails (seed re-run).
            if not verify_pin(user.pin_hash, pin):
                user.pin_hash = hash_pin(pin)
            user.role = role
    await session.flush()


async def authenticate(
    session: AsyncSession, username: str, pin: str
) -> StaffUser | None:
    if is_locked(username):
        return None
    result = await session.execute(select(StaffUser).where(StaffUser.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_pin(user.pin_hash, pin):
        record_failure(username)
        return None
    clear_failures(username)
    return user
