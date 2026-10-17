"""Store pairing code + device token as sha256 hashes only.

Revision ID: 003_auth_token_hashes
Revises: 002_poc_schema
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_auth_token_hashes"
down_revision: str | None = "002_poc_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Demo data: recreate pairing_codes / devices with hash columns.
    op.drop_table("pairing_codes")
    op.drop_table("devices")

    op.create_table(
        "devices",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "paired_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_devices_crew_id", "devices", ["crew_id"])

    op.create_table(
        "pairing_codes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "crew_id", sa.String(64), sa.ForeignKey("crew.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    raise NotImplementedError("003_auth_token_hashes downgrade is not supported")
