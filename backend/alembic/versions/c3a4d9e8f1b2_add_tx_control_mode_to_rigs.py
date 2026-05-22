"""add_tx_control_mode_to_rigs

Revision ID: c3a4d9e8f1b2
Revises: 8c1a0e4d2b9e
Create Date: 2026-03-06 19:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a4d9e8f1b2"
down_revision: Union[str, None] = "8c1a0e4d2b9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("tx_control_mode", sa.String(), nullable=False, server_default="auto")
        )


def downgrade() -> None:
    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.drop_column("tx_control_mode")
