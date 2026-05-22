"""add unique index on tracking_state.name

Revision ID: e1a7c9d2f4b6
Revises: 9c2d1f4a6b8e
Create Date: 2026-04-15 20:05:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1a7c9d2f4b6"
down_revision: Union[str, None] = "9c2d1f4a6b8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_tracking_state_name_unique",
        "tracking_state",
        ["name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_tracking_state_name_unique", table_name="tracking_state")
