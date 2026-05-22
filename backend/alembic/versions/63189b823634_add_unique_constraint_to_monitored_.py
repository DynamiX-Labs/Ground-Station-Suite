"""add_unique_constraint_to_monitored_satellites_norad_id

Revision ID: 63189b823634
Revises: 7b3c47de8a21
Create Date: 2026-01-09 10:04:45.425420

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "63189b823634"
down_revision: Union[str, None] = "7b3c47de8a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, remove any duplicate entries, keeping only the first occurrence
    # This query deletes all but the earliest record for each norad_id
    op.execute(
        """
        DELETE FROM monitored_satellites
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM monitored_satellites
            GROUP BY norad_id
        )
    """
    )

    # Now add the unique constraint
    with op.batch_alter_table("monitored_satellites", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_monitored_satellites_norad_id", ["norad_id"])


def downgrade() -> None:
    # Remove the unique constraint
    with op.batch_alter_table("monitored_satellites", schema=None) as batch_op:
        batch_op.drop_constraint("uq_monitored_satellites_norad_id", type_="unique")
