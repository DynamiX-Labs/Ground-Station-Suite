"""rename_tle_sources_to_orbital_sources

Revision ID: f7b9d2c4e1a6
Revises: c1a9e3f6b4d2
Create Date: 2026-05-02 22:15:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7b9d2c4e1a6"
down_revision: Union[str, None] = "c1a9e3f6b4d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "tle_sources" in table_names and "orbital_sources" not in table_names:
        op.rename_table("tle_sources", "orbital_sources")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "orbital_sources" in table_names and "tle_sources" not in table_names:
        op.rename_table("orbital_sources", "tle_sources")
