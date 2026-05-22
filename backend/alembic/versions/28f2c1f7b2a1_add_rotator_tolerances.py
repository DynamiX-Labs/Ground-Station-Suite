"""add_rotator_tolerances

Revision ID: 28f2c1f7b2a1
Revises: fc7f37f92b40
Create Date: 2026-03-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "28f2c1f7b2a1"
down_revision: Union[str, None] = "fc7f37f92b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rotators",
        sa.Column("aztolerance", sa.Float(), nullable=False, server_default="2.0"),
    )
    op.add_column(
        "rotators",
        sa.Column("eltolerance", sa.Float(), nullable=False, server_default="2.0"),
    )


def downgrade() -> None:
    op.drop_column("rotators", "eltolerance")
    op.drop_column("rotators", "aztolerance")
