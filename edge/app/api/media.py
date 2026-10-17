"""GET /api/v1/media/{media_id} — photos for Master (any) or crew (own tickets)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, get_current_user
from app.db.models import Ticket, TicketMedia
from app.db.session import get_session
from app.errors import AppError

router = APIRouter(tags=["media"])


@router.get("/media/{media_id}")
async def get_media(
    media_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> FileResponse:
    media = await session.get(TicketMedia, media_id)
    if media is None or media.kind != "photo" or not media.local_path:
        raise AppError("not_found", "Media not found", status_code=404)

    ticket = await session.get(Ticket, media.ticket_id)
    if ticket is None:
        raise AppError("not_found", "Media not found", status_code=404)

    if principal.role != "master" and ticket.reporter_crew_id != principal.crew_id:
        raise AppError("forbidden", "Not your ticket media", status_code=403)

    path = Path(media.local_path)
    if not path.is_file():
        raise AppError("not_found", "Media file missing", status_code=404)

    return FileResponse(path, media_type="image/jpeg", filename=f"{media_id}.jpg")
