"""Reporter anonymity and sync request signing. Used identically by edge and shore."""
from __future__ import annotations

import hashlib
import hmac
import time

HEADER_VESSEL_ID = "X-Vessel-Id"
HEADER_TIMESTAMP = "X-Timestamp"
HEADER_SIGNATURE = "X-Signature"
MAX_SKEW_SECONDS = 300


def _b(v: str | bytes) -> bytes:
    return v if isinstance(v, bytes) else v.encode("utf-8")


def reporter_ref(vessel_secret: str | bytes, crew_id: str, ticket_id: str) -> str:
    """Per-ticket pseudonym: HMAC-SHA256(vessel_secret, crew_id + ':' + ticket_id).

    Unique per ticket, so shore cannot link two reports to one person.
    The edge resolves it back by recomputing for the ticket's stored reporter_crew_id.
    """
    digest = hmac.new(_b(vessel_secret), _b(f"{crew_id}:{ticket_id}"), hashlib.sha256).hexdigest()
    return f"rr_{digest[:32]}"


def signing_string(method: str, path: str, timestamp: int, body: bytes) -> bytes:
    """METHOD\\nPATH\\nTIMESTAMP\\nsha256(body). PATH includes the query string."""
    return f"{method.upper()}\n{path}\n{timestamp}\n{hashlib.sha256(body).hexdigest()}".encode()


def sign_request(api_key: str | bytes, method: str, path: str, timestamp: int, body: bytes = b"") -> str:
    return hmac.new(_b(api_key), signing_string(method, path, timestamp, body), hashlib.sha256).hexdigest()


def sync_headers(vessel_id: str, api_key: str | bytes, method: str, path: str, body: bytes = b"",
                 now: int | None = None) -> dict[str, str]:
    ts = int(now if now is not None else time.time())
    return {
        HEADER_VESSEL_ID: vessel_id,
        HEADER_TIMESTAMP: str(ts),
        HEADER_SIGNATURE: sign_request(api_key, method, path, ts, body),
    }


def verify_request(api_key: str | bytes, method: str, path: str, timestamp: int, body: bytes,
                   signature: str, now: int | None = None) -> bool:
    current = int(now if now is not None else time.time())
    if abs(current - int(timestamp)) > MAX_SKEW_SECONDS:
        return False
    expected = sign_request(api_key, method, path, int(timestamp), body)
    return hmac.compare_digest(expected, signature)
