"""GET /learnings, media (Range), POST ack (M5)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from beacon_contract.edge_api import LearningAck, LearningAckResult, LearningCard
from fastapi import APIRouter, Depends, Header
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, get_current_user
from app.config import get_settings
from app.db.models import Learning, LearningMedia
from app.db.models import LearningAck as LearningAckRow
from app.db.session import get_session
from app.errors import AppError
from app.services.learnings import (
    enqueue_learning_stats,
    get_or_create_stats,
    learning_is_listable,
    list_learning_cards,
)

router = APIRouter(prefix="/learnings", tags=["learnings"])


@router.get("", response_model=list[LearningCard])
async def get_learnings(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> list[LearningCard]:
    return await list_learning_cards(
        session, crew_id=principal.crew_id, rank_band=principal.crew.rank_band
    )


@router.get("/{learning_id}/media/{media_id}")
async def get_learning_media(
    learning_id: str,
    media_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    _principal: Annotated[AuthPrincipal, Depends(get_current_user)],
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    learning = await session.get(Learning, learning_id)
    if learning is None or learning.status == "retracted":
        raise AppError("not_found", "Learning not found", status_code=404)

    media = await session.get(LearningMedia, media_id)
    if media is None or media.learning_id != learning_id or not media.local_path:
        raise AppError("not_found", "Media not found", status_code=404)

    path = Path(media.local_path)
    if not path.is_file():
        raise AppError("not_found", "Media file missing", status_code=404)

    media_type = {
        "image": "image/webp",
        "gif_mp4": "video/mp4",
        "video": "video/mp4",
    }.get(media.kind, "application/octet-stream")

    file_size = path.stat().st_size
    if not range_header:
        return FileResponse(path, media_type=media_type, filename=path.name)

    # bytes=start-end
    if not range_header.startswith("bytes="):
        raise AppError("bad_request", "Invalid Range", status_code=416)
    spec = range_header.removeprefix("bytes=").strip()
    start_s, _, end_s = spec.partition("-")
    try:
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
    except ValueError as exc:
        raise AppError("bad_request", "Invalid Range", status_code=416) from exc
    if start < 0 or end >= file_size or start > end:
        raise AppError("bad_request", "Range not satisfiable", status_code=416)

    length = end - start + 1
    with path.open("rb") as f:
        f.seek(start)
        chunk = f.read(length)
    return Response(
        content=chunk,
        status_code=206,
        media_type=media_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        },
    )


@router.post("/{learning_id}/ack", response_model=LearningAckResult)
async def ack_learning(
    learning_id: str,
    body: LearningAck,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> LearningAckResult:
    learning = await session.get(Learning, learning_id)
    if learning is None or learning.status != "published":
        raise AppError("not_found", "Learning not found", status_code=404)

    media = list(
        (
            await session.execute(
                select(LearningMedia).where(LearningMedia.learning_id == learning_id)
            )
        )
        .scalars()
        .all()
    )
    if not learning_is_listable(learning, media):
        raise AppError("not_found", "Learning not ready", status_code=404)

    settings = get_settings()
    now = datetime.now(UTC)
    row = (
        await session.execute(
            select(LearningAckRow).where(
                LearningAckRow.learning_id == learning_id,
                LearningAckRow.crew_id == principal.crew_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = LearningAckRow(
            learning_id=learning_id,
            crew_id=principal.crew_id,
        )
        session.add(row)
        await session.flush()

    stats = await get_or_create_stats(
        session, learning_id=learning_id, vessel_id=settings.vessel_id
    )
    stats_changed = False

    if body.opened and row.opened_at is None:
        row.opened_at = now
        stats.opened += 1
        stats_changed = True

    check_correct: bool | None = None
    if body.check_answer is not None:
        cq = learning.check_question or {}
        correct_index = cq.get("correct_index")
        check_correct = correct_index is not None and int(correct_index) == int(
            body.check_answer
        )
        if row.check_correct is None and check_correct:
            stats.check_correct += 1
            stats_changed = True
        row.check_correct = check_correct

    if body.acked and row.acked_at is None:
        row.acked_at = now
        stats.acknowledged += 1
        stats_changed = True

    if stats_changed:
        await enqueue_learning_stats(session, stats=stats)

    await session.commit()
    return LearningAckResult(check_correct=check_correct)
