"""add_error_logging_to_scheduled_observations

Revision ID: fc7f37f92b40
Revises: 63189b823634
Create Date: 2026-01-14 13:50:10.024639

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fc7f37f92b40"
down_revision: Union[str, None] = "63189b823634"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add error tracking fields
    op.add_column("scheduled_observations", sa.Column("error_message", sa.String(), nullable=True))
    op.add_column(
        "scheduled_observations",
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "scheduled_observations", sa.Column("last_error_time", sa.DateTime(), nullable=True)
    )

    # Add execution metadata fields
    op.add_column(
        "scheduled_observations", sa.Column("actual_start_time", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "scheduled_observations", sa.Column("actual_end_time", sa.DateTime(), nullable=True)
    )
    op.add_column("scheduled_observations", sa.Column("execution_log", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove added columns in reverse order
    op.drop_column("scheduled_observations", "execution_log")
    op.drop_column("scheduled_observations", "actual_end_time")
    op.drop_column("scheduled_observations", "actual_start_time")
    op.drop_column("scheduled_observations", "last_error_time")
    op.drop_column("scheduled_observations", "error_count")
    op.drop_column("scheduled_observations", "error_message")
