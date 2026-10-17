"""Signed HTTP calls to shore-api."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from beacon_contract.security import sync_headers

from app.config import Settings


class ShoreClient:
    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._owns = client is None
        self.http = client or httpx.AsyncClient(
            base_url=settings.shore_url.rstrip("/"),
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    async def aclose(self) -> None:
        if self._owns:
            await self.http.aclose()

    def _headers(self, method: str, path: str, body: bytes = b"") -> dict[str, str]:
        key = self.settings.shore_api_key or "demo-shore-api-key"
        return {
            **sync_headers(self.settings.vessel_id, key, method, path, body),
            "Accept": "application/json",
        }

    async def healthz(self) -> bool:
        try:
            r = await self.http.get("/api/v1/healthz", timeout=3.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def push(self, body_gz: bytes) -> httpx.Response:
        path = "/api/v1/sync/push"
        headers = self._headers("POST", path, body_gz)
        headers["Content-Type"] = "application/json"
        headers["Content-Encoding"] = "gzip"
        return await self.http.post(path, content=body_gz, headers=headers)

    async def pull(self, *, cursor: str | None, limit: int = 200) -> httpx.Response:
        q = {"limit": str(limit)}
        if cursor is not None:
            q["cursor"] = cursor
        qs = urlencode(q)
        path = f"/api/v1/sync/pull?{qs}"
        headers = self._headers("GET", path, b"")
        return await self.http.get(path, headers=headers)

    async def upload_media(self, media_id: str, data: bytes) -> httpx.Response:
        path = f"/api/v1/sync/media/{media_id}"
        headers = self._headers("POST", path, data)
        headers["Content-Type"] = "application/octet-stream"
        return await self.http.post(path, content=data, headers=headers)

    async def media_url(self, learning_media_id: str) -> httpx.Response:
        path = f"/api/v1/sync/media-url/{learning_media_id}"
        headers = self._headers("GET", path, b"")
        return await self.http.get(path, headers=headers)
