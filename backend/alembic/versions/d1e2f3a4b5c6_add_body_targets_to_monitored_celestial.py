"""add body target fields to monitored celestial

Revision ID: d1e2f3a4b5c6
Revises: c8e9f1a2b3d4
Create Date: 2026-04-18 22:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c8e9f1a2b3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "monitored_celestial",
        sa.Column("target_type", sa.String(), nullable=False, server_default="mission"),
    )
    op.add_column("monitored_celestial", sa.Column("body_id", sa.String(), nullable=True))

    with op.batch_alter_table("monitored_celestial") as batch_op:
        batch_op.alter_column("command", existing_type=sa.String(), nullable=True)
        batch_op.create_check_constraint(
            "ck_monitored_celestial_target_type",
            "target_type IN ('mission', 'body')",
        )
        batch_op.create_check_constraint(
            "ck_monitored_celestial_target_fields",
            "(target_type = 'mission' AND command IS NOT NULL AND body_id IS NULL) OR "
            "(target_type = 'body' AND body_id IS NOT NULL AND command IS NULL)",
        )

    op.drop_index("ix_monitored_celestial_command", table_name="monitored_celestial")
    op.create_index(
        "ix_monitored_celestial_command", "monitored_celestial", ["command"], unique=False
    )
    op.create_index(
        "ix_monitored_celestial_target_type", "monitored_celestial", ["target_type"], unique=False
    )
    op.create_index(
        "ix_monitored_celestial_body_id", "monitored_celestial", ["body_id"], unique=False
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_monitored_celestial_mission_command "
        "ON monitored_celestial(command) WHERE target_type = 'mission'"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_monitored_celestial_body_id "
        "ON monitored_celestial(body_id) WHERE target_type = 'body'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_monitored_celestial_body_id")
    op.execute("DROP INDEX IF EXISTS ux_monitored_celestial_mission_command")

    op.drop_index("ix_monitored_celestial_body_id", table_name="monitored_celestial")
    op.drop_index("ix_monitored_celestial_target_type", table_name="monitored_celestial")
    op.drop_index("ix_monitored_celestial_command", table_name="monitored_celestial")
    op.create_index(
        "ix_monitored_celestial_command", "monitored_celestial", ["command"], unique=True
    )

    with op.batch_alter_table("monitored_celestial") as batch_op:
        batch_op.drop_constraint("ck_monitored_celestial_target_fields", type_="check")
        batch_op.drop_constraint("ck_monitored_celestial_target_type", type_="check")
        batch_op.alter_column("command", existing_type=sa.String(), nullable=False)

    op.drop_column("monitored_celestial", "body_id")
    op.drop_column("monitored_celestial", "target_type")
