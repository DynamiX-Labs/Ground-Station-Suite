"""add_retune_and_follow_downlink_to_rigs

Revision ID: e7a1b3f4c9d2
Revises: d41fa9b82c5e
Create Date: 2026-03-07 11:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a1b3f4c9d2"
down_revision: Union[str, None] = "d41fa9b82c5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("retune_interval_ms", sa.Integer(), nullable=False, server_default="2000")
        )
        batch_op.add_column(
            sa.Column(
                "follow_downlink_tuning",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.drop_column("follow_downlink_tuning")
        batch_op.drop_column("retune_interval_ms")
