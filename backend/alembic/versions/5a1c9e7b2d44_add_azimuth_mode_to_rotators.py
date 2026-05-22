"""add azimuth_mode to rotators

Revision ID: 5a1c9e7b2d44
Revises: fc7f37f92b40
Create Date: 2026-03-26 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5a1c9e7b2d44"
down_revision: Union[str, None] = "f2a6c9d1e4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rotators",
        sa.Column("azimuth_mode", sa.String(), nullable=False, server_default="0_360"),
    )


def downgrade() -> None:
    op.drop_column("rotators", "azimuth_mode")
