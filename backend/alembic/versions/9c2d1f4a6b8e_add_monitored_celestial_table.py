"""add monitored celestial table

Revision ID: 9c2d1f4a6b8e
Revises: 4d3a2b1c9f10
Create Date: 2026-04-15 22:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c2d1f4a6b8e"
down_revision: Union[str, None] = "4d3a2b1c9f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "monitored_celestial",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_refresh_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_monitored_celestial_command",
        "monitored_celestial",
        ["command"],
        unique=True,
    )
    op.create_index(
        "ix_monitored_celestial_enabled",
        "monitored_celestial",
        ["enabled"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_monitored_celestial_enabled", table_name="monitored_celestial")
    op.drop_index("ix_monitored_celestial_command", table_name="monitored_celestial")
    op.drop_table("monitored_celestial")
