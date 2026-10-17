"""FastAPI app factory — Beacon edge (POC)."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import auth as auth_api
from app.api import events as events_api
from app.api import health as health_api
from app.api import inbox as inbox_api
from app.api import learnings as learnings_api
from app.api import master as master_api
from app.api import media as media_api
from app.api import reports as reports_api
from app.api import sync as sync_api
from app.api import tickets as tickets_api
from app.auth.jwt_secret import require_jwt_secret
from app.config import get_settings
from app.db.session import init_engine
from app.errors import AppError, app_error_handler
from app.logging import setup_logging

logger = logging.getLogger("beacon.edge")


class AccessLogMiddleware:
    """ASGI access log — never bodies/tokens. Pure ASGI so SSE streams are not buffered."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 500
        method = scope.get("method", "?")
        path = scope.get("path", "?")

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "request",
                extra={
                    "route": f"{method} {path}",
                    "status": status_code,
                    "latency_ms": latency_ms,
                },
            )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    settings = get_settings()
    require_jwt_secret(settings)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_engine(settings.database_url)
    logger.info("edge_started vessel_id=%s", settings.vessel_id)
    yield


def create_app(*, validate_secret: bool = True) -> FastAPI:
    settings = get_settings()
    if validate_secret:
        require_jwt_secret(settings)

    application = FastAPI(title="Beacon Edge", version="0.1.0", lifespan=lifespan)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_middleware(AccessLogMiddleware)

    application.include_router(health_api.router, prefix="/api/v1")
    application.include_router(auth_api.router, prefix="/api/v1")
    application.include_router(master_api.router, prefix="/api/v1")
    application.include_router(reports_api.router, prefix="/api/v1")
    application.include_router(tickets_api.router, prefix="/api/v1")
    application.include_router(inbox_api.router, prefix="/api/v1")
    application.include_router(learnings_api.router, prefix="/api/v1")
    application.include_router(sync_api.router, prefix="/api/v1")
    application.include_router(media_api.router, prefix="/api/v1")
    application.include_router(events_api.router, prefix="/api/v1")

    dist = settings.crew_web_dist
    if dist.is_dir() and (dist / "index.html").exists():
        application.mount("/", StaticFiles(directory=str(dist), html=True), name="crew-web")
    else:

        @application.get("/")
        async def root() -> dict:
            return {
                "service": "beacon-edge",
                "vessel_id": settings.vessel_id,
                "docs": "/docs",
            }

    return application


# Import-safe: lifespan / create_app(validate_secret=True) enforce the secret.
app = create_app(validate_secret=False)
