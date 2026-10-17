"""Draft audio_path + media jsonb for reports flow (M1).

Revision ID: 005_draft_media_paths
Revises: 004_device_pin_lockout
Create Date: 2026-10-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_draft_media_paths"
down_revision: Union[str, None] = "004_device_pin_lockout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("drafts", sa.Column("audio_path", sa.String(512), nullable=True))
    op.add_column("drafts", sa.Column("media", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("drafts", "media")
    op.drop_column("drafts", "audio_path")
