"""Validate BEACON_JWT_SECRET at startup."""

from __future__ import annotations

from app.config import Settings


class JwtSecretError(RuntimeError):
    pass


def require_jwt_secret(settings: Settings) -> None:
    secret = (settings.jwt_secret or "").strip()
    if not secret:
        raise JwtSecretError(
            "BEACON_JWT_SECRET is missing. Set it in the environment "
            '(e.g. python -c "import secrets; print(secrets.token_urlsafe(48))").'
        )
    if len(secret) < 32:
        raise JwtSecretError(
            "BEACON_JWT_SECRET must be at least 32 characters. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
