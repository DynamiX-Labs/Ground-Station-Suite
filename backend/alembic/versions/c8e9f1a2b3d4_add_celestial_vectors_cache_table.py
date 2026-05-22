"""add celestial vectors cache table

Revision ID: c8e9f1a2b3d4
Revises: a4d7c2e9b1f0
Create Date: 2026-04-18 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8e9f1a2b3d4"
down_revision: Union[str, None] = "a4d7c2e9b1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "celestial_vectors_cache",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("epoch_bucket_utc", sa.DateTime(), nullable=False),
        sa.Column("past_hours", sa.Integer(), nullable=False),
        sa.Column("future_hours", sa.Integer(), nullable=False),
        sa.Column("step_minutes", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="horizons"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_celestial_vectors_cache_command",
        "celestial_vectors_cache",
        ["command"],
        unique=False,
    )
    op.create_index(
        "ix_celestial_vectors_cache_epoch_bucket_utc",
        "celestial_vectors_cache",
        ["epoch_bucket_utc"],
        unique=False,
    )
    op.create_index(
        "ix_celestial_vectors_cache_expires_at",
        "celestial_vectors_cache",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_celestial_vectors_cache_lookup",
        "celestial_vectors_cache",
        ["command", "epoch_bucket_utc", "past_hours", "future_hours", "step_minutes"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_celestial_vectors_cache_lookup", table_name="celestial_vectors_cache")
    op.drop_index("ix_celestial_vectors_cache_expires_at", table_name="celestial_vectors_cache")
    op.drop_index(
        "ix_celestial_vectors_cache_epoch_bucket_utc", table_name="celestial_vectors_cache"
    )
    op.drop_index("ix_celestial_vectors_cache_command", table_name="celestial_vectors_cache")
    op.drop_table("celestial_vectors_cache")
