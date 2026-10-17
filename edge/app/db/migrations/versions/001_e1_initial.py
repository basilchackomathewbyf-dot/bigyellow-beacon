"""E1 initial schema — all §4 tables.

Revision ID: 001_e1_initial
Revises:
Create Date: 2026-10-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001_e1_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reporter_ref", sa.String(48), nullable=False, unique=True),
        sa.Column("rank_group", sa.String(32), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("device_label", sa.String(128), nullable=True),
        sa.Column(
            "paired_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "staff_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("pin_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
    )

    op.create_table(
        "pairing_codes",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "near_misses",
        sa.Column("record_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", sa.String(64), nullable=False, unique=True),
        sa.Column("reporter_ref", sa.String(48), nullable=False),
        sa.Column("rank_group", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("original_language", sa.String(16), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("english_text", sa.Text(), nullable=False),
        sa.Column("area", sa.String(64), nullable=False),
        sa.Column("area_detail", sa.String(200), nullable=True),
        sa.Column("hazard_type", sa.String(64), nullable=False),
        sa.Column("ism_report_type", sa.String(64), nullable=False),
        sa.Column("severity_level", sa.String(16), nullable=False),
        sa.Column("potential_consequence", sa.String(64), nullable=False),
        sa.Column("recurring", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column(
            "needs_clarification", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("clarifying_question", postgresql.JSONB(), nullable=True),
        sa.Column("extraction", postgresql.JSONB(), nullable=True),
        sa.Column("state", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("action_text_en", sa.Text(), nullable=True),
        sa.Column("action_owner_rank", sa.String(64), nullable=True),
        sa.Column("action_due", sa.Date(), nullable=True),
        sa.Column(
            "synced_to_shore", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("embedding", Vector(768), nullable=True),
    )
    op.create_index("ix_near_misses_reporter_ref", "near_misses", ["reporter_ref"])

    op.create_table(
        "near_miss_media",
        sa.Column("media_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("near_misses.record_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False, server_default="photo"),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column(
            "uploaded_to_shore", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    op.create_table(
        "near_miss_clarifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("near_misses.record_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", postgresql.JSONB(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "checkin_scores",
        sa.Column("checkin_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reporter_ref", sa.String(48), nullable=False),
        sa.Column("rank_group", sa.String(32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("mood", sa.Integer(), nullable=False),
        sa.Column("fatigue", sa.Integer(), nullable=False),
        sa.Column("workload", sa.Integer(), nullable=False),
        sa.Column("sleep_hours_reported", sa.Float(), nullable=True),
        sa.Column("social_connection", sa.Integer(), nullable=True),
        sa.Column("themes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column(
            "rail_triggered", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("rail_category", sa.String(64), nullable=True),
    )
    op.create_index("ix_checkin_scores_reporter_ref", "checkin_scores", ["reporter_ref"])

    op.create_table(
        "help_requests",
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reporter_ref", sa.String(48), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column(
            "consent_to_contact", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("contact_channel", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
    )

    op.create_table(
        "notices",
        sa.Column("notice_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_by_role", sa.String(32), nullable=False),
        sa.Column("title_en", sa.String(256), nullable=False),
        sa.Column("body_en", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(32), nullable=False, server_default="normal"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source", sa.String(16), nullable=False, server_default="ship"),
    )

    op.create_table(
        "notice_translations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "notice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notices.notice_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lang", sa.String(16), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.UniqueConstraint("notice_id", "lang", name="uq_notice_lang"),
    )

    op.create_table(
        "notice_acks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "notice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notices.notice_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reporter_ref", sa.String(48), nullable=False),
        sa.Column(
            "acked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("notice_id", "reporter_ref", name="uq_notice_ack"),
    )

    op.create_table(
        "fleet_alerts",
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cluster_id", sa.String(64), nullable=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("body_en", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("linked_cases", postgresql.JSONB(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "briefs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("brief_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("brief_date", "source", name="uq_brief_date_source"),
    )

    op.create_table(
        "outbox",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("ref_id", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_delta_id", sa.String(64), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "sync_state",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
    )

    op.create_table(
        "docs",
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(256), nullable=False),
    )

    op.create_table(
        "doc_chunks",
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "doc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("docs.doc_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
    )
    op.create_index("ix_doc_chunks_doc_id", "doc_chunks", ["doc_id"])

    op.create_table(
        "translations_cache",
        sa.Column("sha256", sa.String(64), primary_key=True),
        sa.Column("tgt_lang", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )

    op.create_table(
        "idempotency",
        sa.Column("client_id", sa.String(64), primary_key=True),
        sa.Column("route", sa.String(128), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    for table in (
        "idempotency",
        "translations_cache",
        "doc_chunks",
        "docs",
        "sync_state",
        "outbox",
        "briefs",
        "fleet_alerts",
        "notice_acks",
        "notice_translations",
        "notices",
        "help_requests",
        "checkin_scores",
        "near_miss_clarifications",
        "near_miss_media",
        "near_misses",
        "pairing_codes",
        "staff_users",
        "devices",
    ):
        op.drop_table(table)
