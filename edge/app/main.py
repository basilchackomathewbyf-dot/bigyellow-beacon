"""FastAPI app factory — E1 skeleton."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import auth as auth_api
from app.api import health as health_api
from app.api import ship as ship_api
from app.config import get_settings
from app.db.session import init_engine
from app.errors import AppError, app_error_handler
from app.logging import setup_logging

logger = logging.getLogger("beacon.edge")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log route + status + latency; never bodies."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "request",
            extra={
                "route": f"{request.method} {request.url.path}",
                "status": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_engine(settings.database_url)
    logger.info("edge_started vessel_id=%s", settings.vessel_id)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="Beacon Edge", version="0.1.0", lifespan=lifespan)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_middleware(AccessLogMiddleware)
    # CORS off — same origin on ship LAN (spec §3).

    application.include_router(health_api.router, prefix="/api/v1")
    application.include_router(auth_api.router, prefix="/api/v1")
    application.include_router(ship_api.router, prefix="/api/v1")

    dist = settings.ship_web_dist
    if dist.is_dir() and (dist / "index.html").exists():
        application.mount("/", StaticFiles(directory=str(dist), html=True), name="ship-web")
    else:

        @application.get("/")
        async def root() -> dict:
            return {
                "service": "beacon-edge",
                "vessel_id": settings.vessel_id,
                "docs": "/docs",
            }

    return application


app = create_app()
