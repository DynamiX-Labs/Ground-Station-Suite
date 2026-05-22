"""add color to monitored celestial

Revision ID: a4d7c2e9b1f0
Revises: e1a7c9d2f4b6
Create Date: 2026-04-17 13:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4d7c2e9b1f0"
down_revision: Union[str, None] = "e1a7c9d2f4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("monitored_celestial", sa.Column("color", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("monitored_celestial", "color")
