"""Local mock shore-api for M4 — FastAPI on :9090.

  make mock-shore
  # or: cd edge && .venv/bin/python tools/mock_shore.py
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from beacon_contract.security import (
    HEADER_SIGNATURE,
    HEADER_TIMESTAMP,
    HEADER_VESSEL_ID,
    verify_request,
)
from beacon_contract.sync import (
    LearningMediaUrl,
    PullResponse,
    PushEventAck,
    PushResponse,
    SyncDelta,
)
from fastapi import FastAPI, HTTPException, Query, Request, Response

_REPO = Path(__file__).resolve().parents[2]
_PULL_FIXTURE = _REPO / "contract" / "generated" / "fixtures" / "sync.pull_response.json"

API_KEY = os.environ.get("BEACON_SHORE_API_KEY") or os.environ.get(
    "MOCK_SHORE_API_KEY", "demo-shore-api-key"
)

app = FastAPI(title="Beacon Mock Shore", version="0.1.0")

_processed: set[str] = set()
_pull_served = False


def _signed_path(request: Request) -> str:
    """PATH for HMAC includes the query string (beacon_contract.security)."""
    path = request.url.path
    query = request.url.query
    return f"{path}?{query}" if query else path


def _verify(request: Request, body: bytes) -> None:
    vessel = request.headers.get(HEADER_VESSEL_ID)
    ts = request.headers.get(HEADER_TIMESTAMP)
    sig = request.headers.get(HEADER_SIGNATURE)
    if not vessel or not ts or not sig:
        raise HTTPException(401, detail="missing sync headers")
    if not verify_request(API_KEY, request.method, _signed_path(request), int(ts), body, sig):
        raise HTTPException(401, detail="invalid signature")


@app.get("/api/v1/healthz")
async def healthz() -> dict:
    return {"ok": True, "service": "mock-shore"}


@app.post("/api/v1/sync/push", response_model=PushResponse)
async def sync_push(request: Request) -> PushResponse:
    raw = await request.body()
    _verify(request, raw)

    try:
        if request.headers.get("content-encoding", "").lower() == "gzip" or (
            len(raw) >= 2 and raw[0] == 0x1F and raw[1] == 0x8B
        ):
            raw = gzip.decompress(raw)
        delta = SyncDelta.model_validate_json(raw)
    except Exception as exc:
        raise HTTPException(400, detail=f"invalid SyncDelta: {exc}") from exc

    acks: list[PushEventAck] = []
    for ev in delta.events:
        if ev.event_id in _processed:
            acks.append(PushEventAck(event_id=ev.event_id, status="duplicate"))
        else:
            _processed.add(ev.event_id)
            acks.append(PushEventAck(event_id=ev.event_id, status="applied"))

    return PushResponse(batch_id=delta.batch_id, acks=acks)


@app.get("/api/v1/sync/pull", response_model=PullResponse)
async def sync_pull(
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> PullResponse:
    _verify(request, b"")
    global _pull_served
    if not _pull_served and _PULL_FIXTURE.is_file():
        _pull_served = True
        data = json.loads(_PULL_FIXTURE.read_text(encoding="utf-8"))
        return PullResponse.model_validate(data)
    return PullResponse(changes=[], next_cursor=cursor or "0", has_more=False)


@app.post("/api/v1/sync/media/{ticket_media_id}")
async def sync_media(ticket_media_id: str, request: Request) -> Response:
    raw = await request.body()
    _verify(request, raw)
    return Response(status_code=204)


@app.get("/api/v1/sync/media-url/{learning_media_id}", response_model=LearningMediaUrl)
async def sync_media_url(learning_media_id: str, request: Request) -> LearningMediaUrl:
    _verify(request, b"")
    return LearningMediaUrl(
        media_id=learning_media_id,
        url=f"http://127.0.0.1:9090/mock-media/{learning_media_id}",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )


@app.get("/mock-media/{learning_media_id}")
async def mock_media_bytes(learning_media_id: str) -> Response:
    """Tiny stand-in bytes so the edge can cache learning media locally."""
    # Minimal ISO BMFF-ish / just opaque bytes for the demo cache path.
    payload = b"BEACON_MOCK_LEARNING_MEDIA:" + learning_media_id.encode("utf-8") + b"\x00" * 64
    return Response(content=payload, media_type="video/mp4")


@app.post("/__reset")
async def reset() -> dict:
    """Test helper — clear idempotency + pull-once state."""
    global _pull_served
    _processed.clear()
    _pull_served = False
    return {"ok": True}


def main() -> None:
    import uvicorn

    print(f"mock-shore api_key={API_KEY!r} pull_fixture={_PULL_FIXTURE}")
    uvicorn.run(app, host="0.0.0.0", port=9090, log_level="info")


if __name__ == "__main__":
    main()
