"""add task_start and task_end to scheduled_observations

Revision ID: 7b3c47de8a21
Revises: 6a2b36fdff13
Create Date: 2026-01-06 18:32:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import DateTime

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b3c47de8a21"
down_revision: Union[str, None] = "6a2b36fdff13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add task_start and task_end columns to scheduled_observations
    with op.batch_alter_table("scheduled_observations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("task_start", DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("task_end", DateTime(timezone=True), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_scheduled_observations_task_start"),
            ["task_start"],
            unique=False,
        )


def downgrade() -> None:
    # Remove task_start and task_end columns
    with op.batch_alter_table("scheduled_observations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_scheduled_observations_task_start"))
        batch_op.drop_column("task_end")
        batch_op.drop_column("task_start")
