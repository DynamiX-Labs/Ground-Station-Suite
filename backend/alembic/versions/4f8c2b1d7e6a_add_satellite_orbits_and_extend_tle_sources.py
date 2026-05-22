"""add_satellite_orbits_and_extend_tle_sources

Revision ID: 4f8c2b1d7e6a
Revises: c4d8e2f1b7a9
Create Date: 2026-05-02 13:10:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f8c2b1d7e6a"
down_revision: Union[str, None] = "c4d8e2f1b7a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "satellite_orbits",
        sa.Column("satellite_norad_id", sa.Integer(), nullable=False),
        sa.Column("central_body", sa.String(), nullable=False, server_default="earth"),
        sa.Column("model_kind", sa.String(), nullable=False, server_default="tle"),
        sa.Column("epoch", sa.DateTime(timezone=False), nullable=True),
        sa.Column("tle1", sa.String(), nullable=True),
        sa.Column("tle2", sa.String(), nullable=True),
        sa.Column("omm_payload", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("source_object_id", sa.String(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("added", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=False), nullable=False),
        sa.CheckConstraint(
            "central_body IN ('earth', 'moon', 'mars')",
            name="ck_satellite_orbits_central_body",
        ),
        sa.CheckConstraint("model_kind IN ('tle', 'omm')", name="ck_satellite_orbits_model_kind"),
        sa.CheckConstraint(
            "(model_kind != 'tle') OR (tle1 IS NOT NULL AND tle2 IS NOT NULL)",
            name="ck_satellite_orbits_tle_required_for_tle_model",
        ),
        sa.CheckConstraint(
            "(model_kind != 'omm') OR (omm_payload IS NOT NULL)",
            name="ck_satellite_orbits_omm_payload_required_for_omm_model",
        ),
        sa.ForeignKeyConstraint(
            ["satellite_norad_id"], ["satellites.norad_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["source_id"], ["tle_sources.id"]),
        sa.PrimaryKeyConstraint("satellite_norad_id", "central_body"),
    )
    op.create_index(
        "ix_satellite_orbits_model_kind", "satellite_orbits", ["model_kind"], unique=False
    )
    op.create_index(
        "ix_satellite_orbits_source_id", "satellite_orbits", ["source_id"], unique=False
    )

    with op.batch_alter_table("tle_sources", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("query_mode", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("provider", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("adapter", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("enabled", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("priority", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("central_body", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("auth_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("username", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("password", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("config", sa.JSON(), nullable=True))

    bind = op.get_bind()

    # Populate sane defaults for existing rows before enforcing NOT NULL constraints.
    bind.execute(
        sa.text(
            """
            UPDATE tle_sources
            SET provider = CASE
                WHEN lower(coalesce(url, '')) LIKE '%space-track%' THEN 'space_track'
                WHEN lower(coalesce(url, '')) LIKE '%celestrak%' THEN 'celestrak'
                ELSE 'generic_http'
            END
            WHERE provider IS NULL OR trim(provider) = ''
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE tle_sources
            SET adapter = CASE
                WHEN lower(coalesce(url, '')) LIKE '%space-track%' THEN 'space_track_gp'
                WHEN lower(coalesce(format, '')) = 'omm' THEN 'http_omm'
                ELSE 'http_3le'
            END
            WHERE adapter IS NULL OR trim(adapter) = ''
            """
        )
    )
    bind.execute(sa.text("UPDATE tle_sources SET enabled = 1 WHERE enabled IS NULL"))
    bind.execute(sa.text("UPDATE tle_sources SET priority = 100 WHERE priority IS NULL"))
    bind.execute(
        sa.text(
            "UPDATE tle_sources SET query_mode = 'url' WHERE query_mode IS NULL OR trim(query_mode) = ''"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE tle_sources SET central_body = 'earth' WHERE central_body IS NULL OR trim(central_body) = ''"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE tle_sources SET auth_type = 'none' WHERE auth_type IS NULL OR trim(auth_type) = ''"
        )
    )

    with op.batch_alter_table("tle_sources", schema=None) as batch_op:
        batch_op.alter_column(
            "provider",
            existing_type=sa.String(),
            nullable=False,
            server_default="generic_http",
        )
        batch_op.alter_column(
            "adapter",
            existing_type=sa.String(),
            nullable=False,
            server_default="http_3le",
        )
        batch_op.alter_column(
            "enabled",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default="1",
        )
        batch_op.alter_column(
            "priority",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="100",
        )
        batch_op.alter_column(
            "query_mode",
            existing_type=sa.String(),
            nullable=False,
            server_default="url",
        )
        batch_op.alter_column(
            "central_body",
            existing_type=sa.String(),
            nullable=False,
            server_default="earth",
        )
        batch_op.alter_column(
            "auth_type",
            existing_type=sa.String(),
            nullable=False,
            server_default="none",
        )
        batch_op.create_check_constraint(
            "ck_tle_sources_central_body",
            "central_body IN ('earth', 'moon', 'mars')",
        )
        batch_op.create_check_constraint(
            "ck_tle_sources_auth_type",
            "auth_type IN ('none', 'basic', 'token')",
        )
        batch_op.create_check_constraint(
            "ck_tle_sources_query_mode",
            "query_mode IN ('url', 'group_norad')",
        )
        batch_op.create_foreign_key(
            "fk_tle_sources_group_id_groups",
            "groups",
            ["group_id"],
            ["id"],
        )
        batch_op.create_index("ix_tle_sources_group_id", ["group_id"], unique=False)

    # Backfill the canonical orbit table from legacy per-satellite TLE columns.
    bind.execute(
        sa.text(
            """
            INSERT INTO satellite_orbits (
                satellite_norad_id,
                central_body,
                model_kind,
                epoch,
                tle1,
                tle2,
                omm_payload,
                source_id,
                source_object_id,
                source_updated_at,
                added,
                updated
            )
            SELECT
                s.norad_id,
                'earth',
                'tle',
                NULL,
                s.tle1,
                s.tle2,
                NULL,
                NULL,
                NULL,
                NULL,
                COALESCE(s.added, CURRENT_TIMESTAMP),
                COALESCE(s.updated, s.added, CURRENT_TIMESTAMP)
            FROM satellites s
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "satellite_orbits" in table_names:
        orbit_indexes = {index["name"] for index in inspector.get_indexes("satellite_orbits")}
        if "ix_satellite_orbits_source_id" in orbit_indexes:
            op.drop_index("ix_satellite_orbits_source_id", table_name="satellite_orbits")
        if "ix_satellite_orbits_model_kind" in orbit_indexes:
            op.drop_index("ix_satellite_orbits_model_kind", table_name="satellite_orbits")
        op.drop_table("satellite_orbits")

    source_columns = {column["name"] for column in inspector.get_columns("tle_sources")}
    source_indexes = {index["name"] for index in inspector.get_indexes("tle_sources")}
    source_checks = {
        check["name"]
        for check in inspector.get_check_constraints("tle_sources")
        if check.get("name")
    }
    source_foreign_keys = {
        foreign_key["name"]
        for foreign_key in inspector.get_foreign_keys("tle_sources")
        if foreign_key.get("name")
    }

    with op.batch_alter_table("tle_sources", schema=None) as batch_op:
        if "ix_tle_sources_group_id" in source_indexes:
            batch_op.drop_index("ix_tle_sources_group_id")
        if "fk_tle_sources_group_id_groups" in source_foreign_keys:
            batch_op.drop_constraint("fk_tle_sources_group_id_groups", type_="foreignkey")
        if "ck_tle_sources_query_mode" in source_checks:
            batch_op.drop_constraint("ck_tle_sources_query_mode", type_="check")
        if "ck_tle_sources_auth_type" in source_checks:
            batch_op.drop_constraint("ck_tle_sources_auth_type", type_="check")
        if "ck_tle_sources_central_body" in source_checks:
            batch_op.drop_constraint("ck_tle_sources_central_body", type_="check")
        for column_name in (
            "config",
            "password",
            "username",
            "auth_type",
            "central_body",
            "priority",
            "enabled",
            "adapter",
            "provider",
            "query_mode",
            "group_id",
        ):
            if column_name in source_columns:
                batch_op.drop_column(column_name)
