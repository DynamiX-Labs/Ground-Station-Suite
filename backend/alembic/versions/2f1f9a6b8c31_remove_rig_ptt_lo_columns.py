"""remove_rig_ptt_lo_columns

Revision ID: 2f1f9a6b8c31
Revises: 3f5d2c1b7e1c
Create Date: 2026-02-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f1f9a6b8c31"
down_revision: Union[str, None] = "3f5d2c1b7e1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.drop_column("pttstatus")
        batch_op.drop_column("lodown")
        batch_op.drop_column("loup")


def downgrade() -> None:
    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("loup", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("lodown", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("pttstatus", sa.Integer(), nullable=False, server_default="0")
        )
