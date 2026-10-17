"""Simple in-memory rate limit: 10 req/min per IP for pair + login."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request

from app.errors import AppError

_LIMIT = 10
_WINDOW_S = 60.0

# ip -> deque of monotonic timestamps
_hits: dict[str, deque[float]] = defaultdict(deque)


def reset_rate_limits() -> None:
    """Test helper."""
    _hits.clear()


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def check_auth_rate_limit(request: Request) -> None:
    now = time.monotonic()
    ip = _client_ip(request)
    q = _hits[ip]
    while q and now - q[0] > _WINDOW_S:
        q.popleft()
    if len(q) >= _LIMIT:
        raise AppError(
            "rate_limited",
            "Too many requests; try again shortly",
            status_code=429,
        )
    q.append(now)
