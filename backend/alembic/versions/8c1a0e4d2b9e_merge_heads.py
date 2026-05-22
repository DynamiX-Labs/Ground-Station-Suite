"""merge_heads

Revision ID: 8c1a0e4d2b9e
Revises: 28f2c1f7b2a1, 2f1f9a6b8c31
Create Date: 2026-03-03 00:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "8c1a0e4d2b9e"
down_revision: Union[str, Sequence[str], None] = ("28f2c1f7b2a1", "2f1f9a6b8c31")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
