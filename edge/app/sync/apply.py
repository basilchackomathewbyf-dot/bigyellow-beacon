"""Apply PullChange payloads on the edge."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from beacon_contract import new_id, reporter_ref
from beacon_contract.enums import InboxKind, MessageSender, PullChangeType, SseEvent
from beacon_contract.events import master_channel, vessel_channel
from beacon_contract.sync import (
    AnchorScheduledChange,
    BriefEnrichmentChange,
    FleetAlertChange,
    LearningPublishedChange,
    LearningRetractedChange,
    PullChange,
    RailUpdateChange,
    ShoreMessageChange,
    TicketShoreStatusChange,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import (
    AnchorCard,
    Brief,
    FleetAlert,
    Inbox,
    Learning,
    LearningMedia,
    Ticket,
    TicketMessage,
)
from app.events.emit import emit_message_new, emit_ticket_updated
from app.events.hub import get_hub
from app.sync.client import ShoreClient

logger = logging.getLogger("beacon.edge.sync")


async def resolve_ticket_by_reporter_ref(
    session: AsyncSession, *, vessel_id: str, ref: str, ticket_id: str | None = None
) -> Ticket | None:
    settings = get_settings()
    if ticket_id:
        t = await session.get(Ticket, ticket_id)
        if t is not None and t.vessel_id == vessel_id:
            expected = reporter_ref(settings.vessel_secret, t.reporter_crew_id, t.id)
            if expected == ref or t.reporter_ref == ref:
                return t
    tickets = list(
        (
            await session.execute(select(Ticket).where(Ticket.vessel_id == vessel_id))
        )
        .scalars()
        .all()
    )
    for t in tickets:
        if t.reporter_ref == ref:
            return t
        if reporter_ref(settings.vessel_secret, t.reporter_crew_id, t.id) == ref:
            return t
    return None


async def apply_change(
    session: AsyncSession,
    change: PullChange,
    *,
    client: ShoreClient,
) -> None:
    settings = get_settings()
    typed = change.typed_payload()

    if change.type == PullChangeType.TICKET_SHORE_STATUS:
        assert isinstance(typed, TicketShoreStatusChange)
        ticket = await session.get(Ticket, typed.ticket_id)
        if ticket is None:
            logger.warning("pull_shore_status_missing ticket_id=%s", typed.ticket_id)
            return
        ticket.shore_status = typed.shore_status.value
        if typed.reject_reason is not None:
            ticket.reject_reason = typed.reject_reason.value
        ticket.reject_note = typed.reject_note
        ticket.updated_at = typed.updated_at
        session.add(
            Inbox(
                id=new_id(),
                crew_id=ticket.reporter_crew_id,
                kind=InboxKind.STATUS_CHANGE.value,
                ref_id=ticket.id,
                title=f"Shore status: {typed.shore_status.value}",
                created_at=datetime.now(UTC),
            )
        )
        await session.flush()
        emit_ticket_updated(ticket=ticket, vessel_id=settings.vessel_id)
        return

    if change.type == PullChangeType.TICKET_MESSAGE:
        assert isinstance(typed, ShoreMessageChange)
        ticket = await resolve_ticket_by_reporter_ref(
            session,
            vessel_id=settings.vessel_id,
            ref=typed.reporter_ref,
            ticket_id=typed.ticket_id,
        )
        if ticket is None:
            logger.warning("pull_message_unresolved ref=%s", typed.reporter_ref)
            return
        existing = await session.get(TicketMessage, typed.message_id)
        if existing is None:
            session.add(
                TicketMessage(
                    id=typed.message_id,
                    ticket_id=ticket.id,
                    sender=MessageSender.SHORE.value,
                    body=typed.body,
                    created_at=typed.created_at,
                    updated_at=typed.created_at,
                    origin="shore",
                    version=1,
                )
            )
        session.add(
            Inbox(
                id=new_id(),
                crew_id=ticket.reporter_crew_id,
                kind=InboxKind.SHORE_REPLY.value,
                ref_id=ticket.id,
                title=f"Shore replied on {ticket.ticket_no}",
                created_at=datetime.now(UTC),
            )
        )
        await session.flush()
        emit_message_new(
            ticket=ticket,
            message_id=typed.message_id,
            sender=MessageSender.SHORE.value,
            created_at=typed.created_at,
            vessel_id=settings.vessel_id,
        )
        return

    if change.type == PullChangeType.LEARNING_PUBLISHED:
        assert isinstance(typed, LearningPublishedChange)
        from app.services.learnings import (
            fetch_and_cache_media,
            mark_delivered_and_inbox,
        )

        learning = await session.get(Learning, typed.learning_id)
        if learning is None:
            learning = Learning(
                id=typed.learning_id,
                title=typed.title,
                context=typed.context,
                situation=typed.situation,
                do_points=typed.do_points,
                dont_points=typed.dont_points,
                check_question=typed.check_question.model_dump(mode="json"),
                priority=typed.priority.value,
                rank_filter=typed.rank_filter.value,
                status="published",
                published_at=typed.published_at,
                origin="shore",
                version=1,
            )
            session.add(learning)
        else:
            learning.status = "published"
            learning.title = typed.title
            learning.context = typed.context
            learning.situation = typed.situation
            learning.do_points = typed.do_points
            learning.dont_points = typed.dont_points
            learning.check_question = typed.check_question.model_dump(mode="json")
            learning.priority = typed.priority.value
            learning.rank_filter = typed.rank_filter.value
            learning.published_at = typed.published_at
        for m in typed.media:
            if await session.get(LearningMedia, m.media_id) is None:
                session.add(
                    LearningMedia(
                        id=m.media_id,
                        learning_id=typed.learning_id,
                        kind=m.kind.value,
                        bytes=m.bytes,
                        sha256=m.sha256,
                        duration_s=m.duration_s,
                        origin="shore",
                        version=1,
                    )
                )
        await session.flush()
        ready = await fetch_and_cache_media(session, learning=learning, client=client)
        if not ready:
            logger.warning(
                "learning_media_incomplete learning_id=%s — deferred learning.new",
                typed.learning_id,
            )
            return
        await mark_delivered_and_inbox(session, learning=learning)
        await session.flush()
        channels = [vessel_channel(settings.vessel_id)]
        if typed.priority.value == "urgent":
            channels.append(master_channel(settings.vessel_id))
        get_hub().publish_event(
            channels,
            SseEvent.LEARNING_NEW,
            {"learning_id": typed.learning_id, "priority": typed.priority.value},
        )
        return

    if change.type == PullChangeType.LEARNING_RETRACTED:
        assert isinstance(typed, LearningRetractedChange)
        learning = await session.get(Learning, typed.learning_id)
        if learning is not None:
            learning.status = "retracted"
        return

    if change.type == PullChangeType.FLEET_ALERT:
        assert isinstance(typed, FleetAlertChange)
        if await session.get(FleetAlert, typed.alert_id) is None:
            session.add(
                FleetAlert(
                    alert_id=typed.alert_id,
                    payload=typed.model_dump(mode="json"),
                    received_at=typed.created_at,
                )
            )
        return

    if change.type == PullChangeType.RAIL_UPDATE:
        assert isinstance(typed, RailUpdateChange)
        lex = Path(get_settings().data_dir) / "lexicon_override.json"
        lex.parent.mkdir(parents=True, exist_ok=True)
        lex.write_text(json.dumps(typed.rules), encoding="utf-8")
        # Also try the safety rules path used by rails.
        rules_path = (
            Path(__file__).resolve().parents[1] / "safety" / "rules" / "lexicon.json"
        )
        if rules_path.parent.is_dir():
            # # DECISION: write override alongside shipped lexicon; rails can merge later (M6+).
            (rules_path.parent / "lexicon_pull.json").write_text(
                json.dumps({"version": typed.version, "rules": typed.rules}),
                encoding="utf-8",
            )
        return

    if change.type == PullChangeType.ANCHOR_SCHEDULED:
        assert isinstance(typed, AnchorScheduledChange)
        if await session.get(AnchorCard, typed.card_id) is None:
            session.add(
                AnchorCard(
                    id=typed.card_id,
                    publish_date=typed.publish_date,
                    type=typed.type.value,
                    title=dict(typed.title),
                    body=dict(typed.body),
                    source_name=typed.source_name,
                    source_url=typed.source_url,
                    status="approved",
                    origin="shore",
                    version=1,
                )
            )
            get_hub().publish_event(
                [vessel_channel(settings.vessel_id)],
                SseEvent.ANCHOR_NEW,
                {"card_id": typed.card_id},
            )
        return

    if change.type == PullChangeType.BRIEF_ENRICHMENT:
        assert isinstance(typed, BriefEnrichmentChange)
        brief = await session.get(Brief, typed.brief_date)
        payload = {
            "fleet_context": typed.fleet_context,
            "cluster_ids": typed.cluster_ids,
            "vessel_id": typed.vessel_id,
        }
        if brief is None:
            session.add(Brief(brief_date=typed.brief_date, payload=payload))
        else:
            merged = dict(brief.payload or {})
            merged.update(payload)
            brief.payload = merged
        get_hub().publish_event(
            [master_channel(settings.vessel_id)],
            SseEvent.BRIEF_UPDATED,
            {"brief_date": str(typed.brief_date)},
        )
        return

    logger.warning("pull_unhandled type=%s", change.type)
