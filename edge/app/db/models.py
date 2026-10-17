"""POC schema — Edge + Both tables from TECHNICAL_DESIGN §11, plus edge helpers (M0)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# ---------------------------------------------------------------------------
# Core identity
# ---------------------------------------------------------------------------


class Vessel(Base):
    __tablename__ = "vessels"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    imo: Mapped[str | None] = mapped_column(String(16), nullable=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fleet_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    vessel_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)  # edge only
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="edge")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Crew(Base):
    __tablename__ = "crew"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vessel_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    rank: Mapped[str] = mapped_column(String(64), nullable=False)
    rank_band: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    checkin_reminder_at: Mapped[str] = mapped_column(String(5), nullable=False, default="18:00")
    pin_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_master: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    crew_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("crew.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    paired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_pin_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PairingCode(Base):
    """Plaintext code is never stored — only sha256 hex."""

    __tablename__ = "pairing_codes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    crew_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("crew.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    vessel_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False
    )
    reporter_ref: Mapped[str] = mapped_column(String(48), nullable=False)
    reporter_crew_id: Mapped[str] = mapped_column(String(64), nullable=False)  # edge only
    share_name_with_master: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rank_band: Mapped[str] = mapped_column(String(32), nullable=False)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    description_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_language: Mapped[str] = mapped_column(String(16), nullable=False)
    location_on_board: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hazard_type: Mapped[str] = mapped_column(String(64), nullable=False)
    ism_category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    immediate_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    onboard_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW")
    shore_status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED_FOR_LINK")
    reject_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reject_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="edge")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    media: Mapped[list[TicketMedia]] = relationship(back_populates="ticket")
    actions: Mapped[list[TicketAction]] = relationship(back_populates="ticket")
    messages: Mapped[list[TicketMessage]] = relationship(back_populates="ticket")


class TicketMedia(Base):
    __tablename__ = "ticket_media"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # photo | audio
    local_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    gcs_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="edge")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    ticket: Mapped[Ticket] = relationship(back_populates="media")


class TicketAction(Base):
    __tablename__ = "ticket_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="edge")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    ticket: Mapped[Ticket] = relationship(back_populates="actions")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    sender: Mapped[str] = mapped_column(String(32), nullable=False)  # reporter | master | shore
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="edge")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    ticket: Mapped[Ticket] = relationship(back_populates="messages")


class TicketSeq(Base):
    __tablename__ = "ticket_seq"

    vessel_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# Learnings
# ---------------------------------------------------------------------------


class Learning(Base):
    __tablename__ = "learnings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_ticket_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    do_points: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    dont_points: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    check_question: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    rank_filter: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    ai_drafted_fields: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="shore")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class LearningMedia(Base):
    __tablename__ = "learning_media"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    learning_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("learnings.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    gcs_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    local_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="shore")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class LearningAck(Base):
    __tablename__ = "learning_acks"
    __table_args__ = (UniqueConstraint("learning_id", "crew_id", name="uq_learning_ack"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("learnings.id", ondelete="CASCADE"), nullable=False
    )
    crew_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("crew.id", ondelete="CASCADE"), nullable=False
    )
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class LearningStats(Base):
    __tablename__ = "learning_stats"
    __table_args__ = (UniqueConstraint("learning_id", "vessel_id", name="uq_learning_stats"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("learnings.id", ondelete="CASCADE"), nullable=False
    )
    vessel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    delivered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acknowledged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    check_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="edge")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# ---------------------------------------------------------------------------
# Check-ins / wellbeing (no text column on checkins)
# ---------------------------------------------------------------------------


class Checkin(Base):
    """Scores only — transcripts are never written (privacy rule)."""

    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("crew_id", "ship_date", name="uq_checkin_crew_date"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    crew_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("crew.id", ondelete="CASCADE"), nullable=False
    )
    ship_date: Mapped[date] = mapped_column(Date, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # quick | chat
    mood: Mapped[int] = mapped_column(Integer, nullable=False)
    fatigue: Mapped[int] = mapped_column(Integer, nullable=False)
    workload: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    rail_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tip: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CheckinAggregate(Base):
    __tablename__ = "checkin_aggregates"
    __table_args__ = (UniqueConstraint("vessel_id", "date", name="uq_checkin_agg"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vessel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False)
    mood_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    fatigue_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    workload_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="edge")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# ---------------------------------------------------------------------------
# Daily Anchor
# ---------------------------------------------------------------------------


class AnchorCard(Base):
    __tablename__ = "anchor_cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    publish_date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    audience: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    ai_drafted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="shore")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class AnchorReaction(Base):
    __tablename__ = "anchor_reactions"
    __table_args__ = (UniqueConstraint("card_id", "crew_id", name="uq_anchor_reaction"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("anchor_cards.id", ondelete="CASCADE"), nullable=False
    )
    crew_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("crew.id", ondelete="CASCADE"), nullable=False
    )
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    saved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class AnchorStats(Base):
    __tablename__ = "anchor_stats"
    __table_args__ = (UniqueConstraint("card_id", "vessel_id", name="uq_anchor_stats"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("anchor_cards.id", ondelete="CASCADE"), nullable=False
    )
    vessel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    helpful: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="edge")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# ---------------------------------------------------------------------------
# Welfare / outbox / sync / inbox
# ---------------------------------------------------------------------------


class WelfareRequest(Base):
    __tablename__ = "welfare_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    crew_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("crew.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # event_id uuid7
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    op: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SyncState(Base):
    __tablename__ = "sync_state"

    vessel_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_pull_cursor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_push_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    link_status: Mapped[str] = mapped_column(String(16), nullable=False, default="down")
    link_override: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")
    last_probe_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_pull_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_push_bytes_gz: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pending_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_media: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Inbox(Base):
    __tablename__ = "inbox"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    crew_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("crew.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Edge-only helpers
# ---------------------------------------------------------------------------


class Draft(Base):
    __tablename__ = "drafts"

    draft_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    crew_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("crew.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    transcript_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fields: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    clarifying_question: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Idempotency(Base):
    __tablename__ = "idempotency"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    route: Mapped[str] = mapped_column(String(128), nullable=False)
    crew_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RailHit(Base):
    __tablename__ = "rail_hits"
    __table_args__ = (UniqueConstraint("rule_id", "ship_date", name="uq_rail_hit"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ship_date: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Brief(Base):
    __tablename__ = "briefs"

    brief_date: Mapped[date] = mapped_column(Date, primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FleetAlert(Base):
    __tablename__ = "fleet_alerts"

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
