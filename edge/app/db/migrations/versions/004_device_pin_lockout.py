"""Persist PIN lockout on devices (survives process restart).

Revision ID: 004_device_pin_lockout
Revises: 003_auth_token_hashes
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_device_pin_lockout"
down_revision: str | None = "003_auth_token_hashes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("failed_pin_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "devices",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("devices", "locked_until")
    op.drop_column("devices", "failed_pin_attempts")
