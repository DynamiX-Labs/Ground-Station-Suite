"""normalize_legacy_transmitter_placeholders

Revision ID: a91f8c3d4e2b
Revises: e7a1b3f4c9d2
Create Date: 2026-03-12 16:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a91f8c3d4e2b"
down_revision: Union[str, None] = "e7a1b3f4c9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_to_null(column_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE transmitters
            SET {column_name} = NULL
            WHERE {column_name} IS NOT NULL
              AND LOWER(TRIM(CAST({column_name} AS TEXT))) IN ('', '-', 'null', 'none')
            """
        )
    )


def _normalize_to_bool(column_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE transmitters
            SET {column_name} = 1
            WHERE LOWER(TRIM(CAST({column_name} AS TEXT))) IN ('true', 'yes', 'on')
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE transmitters
            SET {column_name} = 0
            WHERE LOWER(TRIM(CAST({column_name} AS TEXT))) IN ('false', 'no', 'off')
            """
        )
    )


def upgrade() -> None:
    # Optional integer-like fields
    _normalize_to_null("uplink_low")
    _normalize_to_null("uplink_high")
    _normalize_to_null("downlink_low")
    _normalize_to_null("downlink_high")
    _normalize_to_null("uplink_drift")
    _normalize_to_null("downlink_drift")
    _normalize_to_null("baud")

    # Optional boolean-like fields
    _normalize_to_null("alive")
    _normalize_to_null("invert")
    _normalize_to_bool("alive")
    _normalize_to_bool("invert")

    # Optional string-like field used by transmitter edit/add dialog
    _normalize_to_null("uplink_mode")


def downgrade() -> None:
    # Data normalization is intentionally not reverted.
    pass
