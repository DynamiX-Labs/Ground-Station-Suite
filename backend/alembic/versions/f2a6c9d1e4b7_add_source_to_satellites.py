"""add_source_to_satellites

Revision ID: f2a6c9d1e4b7
Revises: b6d4e2f1a9c3
Create Date: 2026-03-12 19:10:00.000000

"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a6c9d1e4b7"
down_revision: Union[str, None] = "b6d4e2f1a9c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_satellite_ids(raw_value):
    if raw_value is None:
        return []

    # Depending on dialect/driver, JSON columns can arrive as Python lists or strings.
    value = raw_value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            value = json.loads(value)
        except Exception:
            return []

    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        try:
            normalized.append(int(item))
        except Exception:
            continue
    return normalized


def upgrade() -> None:
    with op.batch_alter_table("satellites", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(), nullable=True))

    bind = op.get_bind()

    # Baseline: treat all legacy satellites as manual first.
    bind.execute(
        sa.text("UPDATE satellites SET source = 'manual' WHERE source IS NULL OR TRIM(source) = ''")
    )

    # Promote satellites linked to system/TLE groups to tlesync.
    groups_result = bind.execute(
        sa.text(
            """
            SELECT identifier, satellite_ids
            FROM groups
            WHERE identifier IS NOT NULL
              AND TRIM(identifier) <> ''
              AND satellite_ids IS NOT NULL
            """
        )
    )

    for row in groups_result:
        satellite_ids = _normalize_satellite_ids(row.satellite_ids)
        if not satellite_ids:
            continue

        bind.execute(
            sa.text("UPDATE satellites SET source = 'tlesync' WHERE norad_id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": satellite_ids},
        )

    with op.batch_alter_table("satellites", schema=None) as batch_op:
        batch_op.alter_column(
            "source", existing_type=sa.String(), nullable=False, server_default="manual"
        )


def downgrade() -> None:
    with op.batch_alter_table("satellites", schema=None) as batch_op:
        batch_op.drop_column("source")
