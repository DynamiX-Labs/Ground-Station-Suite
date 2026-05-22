"""add rotator park positions

Revision ID: 4d3a2b1c9f10
Revises: 5a1c9e7b2d44
Create Date: 2026-04-11 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d3a2b1c9f10"
down_revision: Union[str, None] = "5a1c9e7b2d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rotators", sa.Column("parkaz", sa.Float(), nullable=True))
    op.add_column("rotators", sa.Column("parkel", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("rotators", "parkel")
    op.drop_column("rotators", "parkaz")
