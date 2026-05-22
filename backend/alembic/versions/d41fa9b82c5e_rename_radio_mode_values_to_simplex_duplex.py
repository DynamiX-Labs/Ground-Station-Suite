"""rename_radio_mode_values_to_simplex_duplex

Revision ID: d41fa9b82c5e
Revises: b7e2d4c913aa
Create Date: 2026-03-06 19:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d41fa9b82c5e"
down_revision: Union[str, None] = "b7e2d4c913aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE rigs SET radio_mode='simplex' WHERE radio_mode='single_path'")
    )
    connection.execute(sa.text("UPDATE rigs SET radio_mode='duplex' WHERE radio_mode='dual_path'"))

    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.alter_column("radio_mode", server_default="duplex")


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE rigs SET radio_mode='single_path' WHERE radio_mode='simplex'")
    )
    connection.execute(sa.text("UPDATE rigs SET radio_mode='dual_path' WHERE radio_mode='duplex'"))

    with op.batch_alter_table("rigs", schema=None) as batch_op:
        batch_op.alter_column("radio_mode", server_default="dual_path")
