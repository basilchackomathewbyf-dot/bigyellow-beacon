"""GET /inbox, POST /inbox/{id}/read (M3)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from beacon_contract.edge_api import InboxItem
from beacon_contract.enums import InboxKind
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthPrincipal, get_current_user
from app.db.models import Inbox
from app.db.session import get_session
from app.errors import AppError

router = APIRouter(prefix="/inbox", tags=["inbox"])


def _item(row: Inbox) -> InboxItem:
    return InboxItem(
        inbox_id=row.id,
        kind=InboxKind(row.kind),
        ref_id=row.ref_id or row.id,
        title=row.title,
        created_at=row.created_at,
        read_at=row.read_at,
    )


@router.get("", response_model=list[InboxItem])
async def list_inbox(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> list[InboxItem]:
    """Unread inbox items for the current crew member."""
    rows = (
        await session.execute(
            select(Inbox)
            .where(Inbox.crew_id == principal.crew_id, Inbox.read_at.is_(None))
            .order_by(Inbox.created_at.desc())
        )
    ).scalars().all()
    return [_item(r) for r in rows]


@router.post("/{inbox_id}/read", response_model=InboxItem)
async def mark_read(
    inbox_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(get_current_user)],
) -> InboxItem:
    row = await session.get(Inbox, inbox_id)
    if row is None or row.crew_id != principal.crew_id:
        raise AppError("not_found", "Inbox item not found", status_code=404)
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(row)
    return _item(row)
