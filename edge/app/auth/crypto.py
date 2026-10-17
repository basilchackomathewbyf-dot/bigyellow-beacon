"""Hashing helpers — never log inputs."""

from __future__ import annotations

import hashlib
import secrets


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_device_token() -> str:
    """32 random bytes, urlsafe (no padding issues for IndexedDB storage)."""
    return secrets.token_urlsafe(32)


def normalize_pairing_code(code: str) -> str:
    return code.strip().upper()
