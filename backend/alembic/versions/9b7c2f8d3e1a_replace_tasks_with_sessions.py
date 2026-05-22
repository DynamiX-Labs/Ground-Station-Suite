"""replace tasks with sessions for observations and monitored satellites

Revision ID: 9b7c2f8d3e1a
Revises: fc7f37f92b40
Create Date: 2026-02-01 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b7c2f8d3e1a"
down_revision: Union[str, None] = "fc7f37f92b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrate_sessions(connection, table_name: str) -> None:
    table = sa.table(
        table_name,
        sa.column("id", sa.String()),
        sa.column("hardware_config", sa.JSON()),
        sa.column("tasks", sa.JSON()),
        sa.column("sessions", sa.JSON()),
    )

    rows = connection.execute(sa.select(table.c.id, table.c.hardware_config, table.c.tasks))
    for row in rows:
        hardware_config = row.hardware_config or {}
        tasks = row.tasks or []
        sdr_config = hardware_config.get("sdr", {}) if isinstance(hardware_config, dict) else {}
        sessions = [{"sdr": sdr_config or {}, "tasks": tasks}]
        connection.execute(table.update().where(table.c.id == row.id).values(sessions=sessions))


def upgrade() -> None:
    with op.batch_alter_table("monitored_satellites", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sessions", sa.JSON(), nullable=True))

    with op.batch_alter_table("scheduled_observations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sessions", sa.JSON(), nullable=True))

    connection = op.get_bind()
    _migrate_sessions(connection, "monitored_satellites")
    _migrate_sessions(connection, "scheduled_observations")

    with op.batch_alter_table("monitored_satellites", schema=None) as batch_op:
        batch_op.drop_column("tasks")
        batch_op.alter_column("sessions", nullable=False)

    with op.batch_alter_table("scheduled_observations", schema=None) as batch_op:
        batch_op.drop_column("tasks")
        batch_op.alter_column("sessions", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("monitored_satellites", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tasks", sa.JSON(), nullable=True))

    with op.batch_alter_table("scheduled_observations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tasks", sa.JSON(), nullable=True))

    connection = op.get_bind()
    monitored = sa.table(
        "monitored_satellites",
        sa.column("id", sa.String()),
        sa.column("sessions", sa.JSON()),
        sa.column("tasks", sa.JSON()),
    )
    scheduled = sa.table(
        "scheduled_observations",
        sa.column("id", sa.String()),
        sa.column("sessions", sa.JSON()),
        sa.column("tasks", sa.JSON()),
    )

    for table in (monitored, scheduled):
        rows = connection.execute(sa.select(table.c.id, table.c.sessions))
        for row in rows:
            sessions = row.sessions or []
            tasks: list = []
            if sessions:
                first = sessions[0] or {}
                tasks = first.get("tasks", []) if isinstance(first, dict) else []
            connection.execute(table.update().where(table.c.id == row.id).values(tasks=tasks))

    with op.batch_alter_table("monitored_satellites", schema=None) as batch_op:
        batch_op.drop_column("sessions")
        batch_op.alter_column("tasks", nullable=False)

    with op.batch_alter_table("scheduled_observations", schema=None) as batch_op:
        batch_op.drop_column("sessions")
        batch_op.alter_column("tasks", nullable=False)
