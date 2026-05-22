"""normalize_transmitter_itu_notification_json

Revision ID: b6d4e2f1a9c3
Revises: a91f8c3d4e2b
Create Date: 2026-03-12 16:55:00.000000

"""

import json
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6d4e2f1a9c3"
down_revision: Union[str, None] = "a91f8c3d4e2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_itu_notification_value(raw_value):
    if raw_value is None:
        return None
    if isinstance(raw_value, (dict, list, bool, int, float)):
        return raw_value
    if not isinstance(raw_value, str):
        return None

    candidate = raw_value.strip()
    if candidate.lower() in {"", "-", "null", "none"}:
        return None

    for _ in range(3):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            if candidate.startswith('"') and candidate.endswith('"'):
                candidate = candidate[1:-1].replace('\\\\"', '"')
                continue
            return None

        if isinstance(parsed, str):
            candidate = parsed
            continue
        return parsed

    return None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, itu_notification
            FROM transmitters
            WHERE itu_notification IS NOT NULL
              AND json_valid(CAST(itu_notification AS TEXT)) = 0
            """
        )
    ).fetchall()

    for row in rows:
        normalized = _normalize_itu_notification_value(row.itu_notification)
        bind.execute(
            sa.text("UPDATE transmitters SET itu_notification = :val WHERE id = :id"),
            {"id": row.id, "val": json.dumps(normalized) if normalized is not None else None},
        )


def downgrade() -> None:
    # Data normalization is intentionally not reverted.
    pass
