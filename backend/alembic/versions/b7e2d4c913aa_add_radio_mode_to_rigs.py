"""add_radio_mode_to_rigs

Revision ID: b7e2d4c913aa
Revises: c3a4d9e8f1b2
Create Date: 2026-03-06 19:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2d4c913aa"
down_revision: Union[str, None] = "c3a4d9e8f1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("radio_mode", sa.String(), nullable=False, server_default="dual_path")
        )


def downgrade() -> None:
    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.drop_column("radio_mode")
