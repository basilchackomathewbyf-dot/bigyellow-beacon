"""POC schema — drop E1/E4 tables; create §11 Edge+Both + helpers.

Revision ID: 002_poc_schema
Revises: 001_e1_initial
Create Date: 2026-10-17

Demo data only, so old tables are dropped rather than migrated.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "002_poc_schema"
down_revision: Union[str, None] = "001_e1_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_TABLES = (
    "near_miss_clarifications",
    "near_miss_media",
    "near_misses",
    "notice_acks",
    "notice_translations",
    "notices",
    "help_requests",
    "checkin_scores",
    "doc_chunks",
    "docs",
    "translations_cache",
    "fleet_alerts",
    "briefs",
    "outbox",
    "sync_state",
    "idempotency",
    "pairing_codes",
    "devices",
    "staff_users",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    for table in _OLD_TABLES:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    # -- vessels / crew / devices / pairing ---------------------------------
    op.create_table(
        "vessels",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("imo", sa.String(16), nullable=True),
        sa.Column("type", sa.String(64), nullable=True),
        sa.Column("fleet_group", sa.String(64), nullable=True),
        sa.Column("api_key_hash", sa.String(256), nullable=True),
        sa.Column("vessel_secret", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="edge"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "crew",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("vessel_id", sa.String(64), sa.ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("rank", sa.String(64), nullable=False),
        sa.Column("rank_band", sa.String(32), nullable=False),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("checkin_reminder_at", sa.String(5), nullable=False, server_default="18:00"),
        sa.Column("pin_hash", sa.String(256), nullable=True),
        sa.Column("is_master", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paired_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_devices_crew_id", "devices", ["crew_id"])

    op.create_table(
        "pairing_codes",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column("crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -- tickets ------------------------------------------------------------
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("ticket_no", sa.String(32), nullable=False, unique=True),
        sa.Column("vessel_id", sa.String(64), sa.ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reporter_ref", sa.String(48), nullable=False),
        sa.Column("reporter_crew_id", sa.String(64), nullable=False),
        sa.Column("share_name_with_master", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rank_band", sa.String(32), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=False),
        sa.Column("description_original", sa.Text(), nullable=True),
        sa.Column("original_language", sa.String(16), nullable=False),
        sa.Column("location_on_board", sa.String(200), nullable=True),
        sa.Column("hazard_type", sa.String(64), nullable=False),
        sa.Column("ism_category", sa.String(64), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("immediate_action", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("onboard_status", sa.String(32), nullable=False, server_default="NEW"),
        sa.Column("shore_status", sa.String(32), nullable=False, server_default="QUEUED_FOR_LINK"),
        sa.Column("reject_reason", sa.String(64), nullable=True),
        sa.Column("reject_note", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.String(64), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="edge"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "ticket_media",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("ticket_id", sa.String(64), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("local_path", sa.String(512), nullable=True),
        sa.Column("gcs_uri", sa.String(512), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("synced", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="edge"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "ticket_actions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("ticket_id", sa.String(64), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_role", sa.String(32), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("responsible_rank", sa.String(64), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="edge"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "ticket_messages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("ticket_id", sa.String(64), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender", sa.String(32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="edge"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "ticket_seq",
        sa.Column("vessel_id", sa.String(64), primary_key=True),
        sa.Column("last_seq", sa.Integer(), nullable=False, server_default="0"),
    )

    # -- learnings ----------------------------------------------------------
    op.create_table(
        "learnings",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_ticket_id", sa.String(64), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("situation", sa.Text(), nullable=True),
        sa.Column("do_points", postgresql.JSONB(), nullable=True),
        sa.Column("dont_points", postgresql.JSONB(), nullable=True),
        sa.Column("check_question", postgresql.JSONB(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("priority", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("rank_filter", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("ai_drafted_fields", postgresql.JSONB(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="shore"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "learning_media",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("learning_id", sa.String(64), sa.ForeignKey("learnings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("gcs_uri", sa.String(512), nullable=True),
        sa.Column("local_path", sa.String(512), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="shore"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "learning_acks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("learning_id", sa.String(64), sa.ForeignKey("learnings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_correct", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("learning_id", "crew_id", name="uq_learning_ack"),
    )

    op.create_table(
        "learning_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("learning_id", sa.String(64), sa.ForeignKey("learnings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vessel_id", sa.String(64), nullable=False),
        sa.Column("delivered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("acknowledged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("check_correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="edge"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("learning_id", "vessel_id", name="uq_learning_stats"),
    )

    # -- checkins (no text column) ------------------------------------------
    op.create_table(
        "checkins",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ship_date", sa.Date(), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("mood", sa.Integer(), nullable=False),
        sa.Column("fatigue", sa.Integer(), nullable=False),
        sa.Column("workload", sa.Integer(), nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("rail_hit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tip", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("crew_id", "ship_date", name="uq_checkin_crew_date"),
    )

    op.create_table(
        "checkin_aggregates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("vessel_id", sa.String(64), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("mood_avg", sa.Float(), nullable=True),
        sa.Column("fatigue_avg", sa.Float(), nullable=True),
        sa.Column("workload_avg", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="edge"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("vessel_id", "date", name="uq_checkin_agg"),
    )

    # -- anchor -------------------------------------------------------------
    op.create_table(
        "anchor_cards",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("publish_date", sa.Date(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", postgresql.JSONB(), nullable=False),
        sa.Column("body", postgresql.JSONB(), nullable=False),
        sa.Column("source_name", sa.String(128), nullable=True),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("image_uri", sa.String(512), nullable=True),
        sa.Column("audience", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("ai_drafted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_seed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="shore"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "anchor_reactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("card_id", sa.String(64), sa.ForeignKey("anchor_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("helpful", sa.Boolean(), nullable=True),
        sa.Column("saved", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("card_id", "crew_id", name="uq_anchor_reaction"),
    )

    op.create_table(
        "anchor_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("card_id", sa.String(64), sa.ForeignKey("anchor_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vessel_id", sa.String(64), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("helpful", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="edge"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("card_id", "vessel_id", name="uq_anchor_stats"),
    )

    # -- welfare / outbox / sync / inbox ------------------------------------
    op.create_table(
        "welfare_requests",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "outbox",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("entity", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("op", sa.String(16), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "sync_state",
        sa.Column("vessel_id", sa.String(64), primary_key=True),
        sa.Column("last_pull_cursor", sa.String(128), nullable=True),
        sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("link_status", sa.String(16), nullable=False, server_default="down"),
        sa.Column("link_override", sa.String(16), nullable=False, server_default="auto"),
        sa.Column("last_probe_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_pull_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_push_bytes_gz", sa.Integer(), nullable=True),
        sa.Column("pending_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_media", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "inbox",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("ref_id", sa.String(64), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_inbox_crew_id", "inbox", ["crew_id"])

    # -- edge helpers -------------------------------------------------------
    op.create_table(
        "drafts",
        sa.Column("draft_id", sa.String(64), primary_key=True),
        sa.Column("crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("transcript_original", sa.Text(), nullable=True),
        sa.Column("original_language", sa.String(16), nullable=True),
        sa.Column("fields", postgresql.JSONB(), nullable=True),
        sa.Column("clarifying_question", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "idempotency",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("route", sa.String(128), nullable=False),
        sa.Column("crew_id", sa.String(64), nullable=True),
        sa.Column("response", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "rail_hits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rule_id", sa.String(64), nullable=False),
        sa.Column("ship_date", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("rule_id", "ship_date", name="uq_rail_hit"),
    )

    op.create_table(
        "briefs",
        sa.Column("brief_date", sa.Date(), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "fleet_alerts",
        sa.Column("alert_id", sa.String(64), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Demo-only: downgrade is not supported; re-run 001 from a fresh DB.
    raise NotImplementedError("002_poc_schema downgrade is not supported (demo data)")
