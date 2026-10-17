"""SQLAlchemy models — all tables from edge spec §4."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    reporter_ref: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    rank_group: Mapped[str] = mapped_column(String(32), nullable=False, default="undisclosed")
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    device_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StaffUser(Base):
    __tablename__ = "staff_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # master | safety_officer


class PairingCode(Base):
    __tablename__ = "pairing_codes"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class NearMiss(Base):
    __tablename__ = "near_misses"

    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    reporter_ref: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    rank_group: Mapped[str] = mapped_column(String(32), nullable=False, default="undisclosed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    original_language: Mapped[str] = mapped_column(String(16), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    english_text: Mapped[str] = mapped_column(Text, nullable=False)
    area: Mapped[str] = mapped_column(String(64), nullable=False)
    area_detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hazard_type: Mapped[str] = mapped_column(String(64), nullable=False)
    ism_report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity_level: Mapped[str] = mapped_column(String(16), nullable=False)
    potential_consequence: Mapped[str] = mapped_column(String(64), nullable=False)
    recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    needs_clarification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clarifying_question: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    action_text_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_owner_rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    synced_to_shore: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

    media: Mapped[list[NearMissMedia]] = relationship(back_populates="near_miss")
    clarifications: Mapped[list[NearMissClarification]] = relationship(back_populates="near_miss")


class NearMissMedia(Base):
    __tablename__ = "near_miss_media"

    media_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("near_misses.record_id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="photo")
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_to_shore: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    near_miss: Mapped[NearMiss] = relationship(back_populates="media")


class NearMissClarification(Base):
    __tablename__ = "near_miss_clarifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("near_misses.record_id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    near_miss: Mapped[NearMiss] = relationship(back_populates="clarifications")


class CheckinScore(Base):
    """Scores only — no text columns (privacy rule)."""

    __tablename__ = "checkin_scores"

    checkin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    reporter_ref: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    rank_group: Mapped[str] = mapped_column(String(32), nullable=False, default="undisclosed")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    mood: Mapped[int] = mapped_column(Integer, nullable=False)
    fatigue: Mapped[int] = mapped_column(Integer, nullable=False)
    workload: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_hours_reported: Mapped[float | None] = mapped_column(Float, nullable=True)
    social_connection: Mapped[int | None] = mapped_column(Integer, nullable=True)
    themes: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # ai | quick
    rail_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rail_category: Mapped[str | None] = mapped_column(String(64), nullable=True)


class HelpRequest(Base):
    __tablename__ = "help_requests"

    escalation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    reporter_ref: Mapped[str] = mapped_column(String(48), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    consent_to_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contact_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DECISION: ship medical ack status for E6 medical alerts
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")


class Notice(Base):
    __tablename__ = "notices"

    notice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    created_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    title_en: Mapped[str] = mapped_column(String(256), nullable=False)
    body_en: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="ship")  # ship | shore


class NoticeTranslation(Base):
    __tablename__ = "notice_translations"
    __table_args__ = (UniqueConstraint("notice_id", "lang", name="uq_notice_lang"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notices.notice_id", ondelete="CASCADE"), nullable=False
    )
    lang: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class NoticeAck(Base):
    __tablename__ = "notice_acks"
    __table_args__ = (UniqueConstraint("notice_id", "reporter_ref", name="uq_notice_ack"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notices.notice_id", ondelete="CASCADE"), nullable=False
    )
    reporter_ref: Mapped[str] = mapped_column(String(48), nullable=False)
    acked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FleetAlert(Base):
    __tablename__ = "fleet_alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    cluster_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body_en: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    linked_cases: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Brief(Base):
    __tablename__ = "briefs"
    __table_args__ = (UniqueConstraint("brief_date", "source", name="uq_brief_date_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brief_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # edge | shore_enriched
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Outbox(Base):
    __tablename__ = "outbox"

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_delta_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SyncState(Base):
    __tablename__ = "sync_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)


class Doc(Base):
    __tablename__ = "docs"

    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(256), nullable=False)


class DocChunk(Base):
    __tablename__ = "doc_chunks"

    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("docs.doc_id", ondelete="CASCADE"), nullable=False
    )
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

    __table_args__ = (Index("ix_doc_chunks_doc_id", "doc_id"),)


class TranslationsCache(Base):
    __tablename__ = "translations_cache"

    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    tgt_lang: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)


class Idempotency(Base):
    __tablename__ = "idempotency"

    client_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    route: Mapped[str] = mapped_column(String(128), nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

