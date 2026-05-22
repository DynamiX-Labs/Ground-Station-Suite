"""refactor: move generated observation tracking to scheduled_observations table

Revision ID: 6a2b36fdff13
Revises: 16019e90ddb7
Create Date: 2026-01-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import DateTime

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a2b36fdff13"
down_revision: Union[str, None] = "16019e90ddb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to scheduled_observations
    with op.batch_alter_table("scheduled_observations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("monitored_satellite_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("generated_at", DateTime(timezone=False), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_scheduled_observations_monitored_satellite_id"),
            ["monitored_satellite_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_scheduled_observations_monitored_satellite_id",
            "monitored_satellites",
            ["monitored_satellite_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Migrate data from generated_observations to scheduled_observations
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
        UPDATE scheduled_observations
        SET monitored_satellite_id = go.monitored_satellite_id,
            generated_at = go.generated_at
        FROM generated_observations go
        WHERE scheduled_observations.id = go.observation_id
    """
        )
    )

    # Drop the generated_observations table
    op.drop_table("generated_observations")


def downgrade() -> None:
    # Recreate generated_observations table
    op.create_table(
        "generated_observations",
        sa.Column("observation_id", sa.String(), nullable=False),
        sa.Column("monitored_satellite_id", sa.String(), nullable=False),
        sa.Column("generated_at", DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["monitored_satellite_id"], ["monitored_satellites.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["scheduled_observations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("observation_id"),
    )
    with op.batch_alter_table("generated_observations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_generated_observations_monitored_satellite_id"),
            ["monitored_satellite_id"],
            unique=False,
        )

    # Migrate data back from scheduled_observations to generated_observations
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
        INSERT INTO generated_observations (observation_id, monitored_satellite_id, generated_at)
        SELECT id, monitored_satellite_id, generated_at
        FROM scheduled_observations
        WHERE monitored_satellite_id IS NOT NULL
    """
        )
    )

    # Remove columns from scheduled_observations
    with op.batch_alter_table("scheduled_observations", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_scheduled_observations_monitored_satellite_id", type_="foreignkey"
        )
        batch_op.drop_index(batch_op.f("ix_scheduled_observations_monitored_satellite_id"))
        batch_op.drop_column("generated_at")
        batch_op.drop_column("monitored_satellite_id")
