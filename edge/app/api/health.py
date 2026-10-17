"""GET /api/v1/healthz and /api/v1/health alias."""

from __future__ import annotations

from beacon_contract.edge_api import Healthz
from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["health"])


def _healthz() -> Healthz:
    settings = get_settings()
    ai_mode = "ollama" if settings.ai == "ollama" else "fake"
    # Models reported ready only when BEACON_AI=ollama; fake mode is always degraded for models.
    models_ready = settings.ai == "ollama"
    return Healthz(
        status="ok",
        edge_version=__version__,
        models={"gemma": models_ready, "whisper": models_ready, "embeddings": models_ready},
        ai_mode=ai_mode,  # type: ignore[arg-type]
    )


@router.get("/healthz", response_model=Healthz)
async def healthz() -> Healthz:
    return _healthz()


@router.get("/health", response_model=Healthz)
async def health() -> Healthz:
    """Alias of /healthz (kept for older clients)."""
    return _healthz()
