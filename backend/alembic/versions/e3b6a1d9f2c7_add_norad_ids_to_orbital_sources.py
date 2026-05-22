"""add_norad_ids_to_orbital_sources

Revision ID: e3b6a1d9f2c7
Revises: f7b9d2c4e1a6
Create Date: 2026-05-03 12:00:00.000000

"""

from __future__ import annotations

import json
import re
from typing import Any, Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3b6a1d9f2c7"
down_revision: Union[str, None] = "f7b9d2c4e1a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_norad_ids(value: Any) -> list[int]:
    candidate = value
    if isinstance(candidate, str):
        cleaned = candidate.strip()
        if not cleaned:
            return []
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, str):
                candidate = re.split(r"[\s,]+", parsed.strip())
            else:
                candidate = parsed
        except json.JSONDecodeError:
            candidate = re.split(r"[\s,]+", cleaned)
    elif candidate is None:
        return []
    elif isinstance(candidate, (int, float)):
        candidate = [candidate]

    if not isinstance(candidate, (list, tuple, set)):
        return []

    normalized: list[int] = []
    seen: set[int] = set()
    for item in candidate:
        try:
            norad_id = int(item)
        except (TypeError, ValueError):
            continue
        if norad_id <= 0 or norad_id in seen:
            continue
        normalized.append(norad_id)
        seen.add(norad_id)
    return normalized


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "orbital_sources" not in table_names:
        return

    source_columns = {column["name"] for column in inspector.get_columns("orbital_sources")}
    if "norad_ids" not in source_columns:
        with op.batch_alter_table("orbital_sources", schema=None) as batch_op:
            batch_op.add_column(sa.Column("norad_ids", sa.JSON(), nullable=True))

    metadata = sa.MetaData()
    orbital_sources = sa.Table("orbital_sources", metadata, autoload_with=bind)
    groups = sa.Table("groups", metadata, autoload_with=bind)

    # SQLite may reflect UUID columns with NUMERIC affinity and attempt Decimal coercion
    # for string UUID values. Read with explicit text casts to avoid result processors.
    source_rows = bind.execute(
        sa.text(
            """
            SELECT
                CAST(id AS TEXT) AS id,
                provider,
                adapter,
                CAST(group_id AS TEXT) AS group_id,
                norad_ids
            FROM orbital_sources
            """
        )
    ).mappings()

    group_cache: dict[str, list[int]] = {}
    for row in source_rows:
        provider = str(row.get("provider") or "").strip().lower()
        adapter = str(row.get("adapter") or "").strip().lower()
        if provider != "space_track" and adapter != "space_track_gp":
            continue

        source_id = row.get("id")
        if source_id is None:
            continue

        current_norad_ids = _normalize_norad_ids(row.get("norad_ids"))
        if current_norad_ids:
            bind.execute(
                sa.update(orbital_sources)
                .where(sa.cast(orbital_sources.c.id, sa.String()) == str(source_id))
                .values(query_mode="url")
            )
            continue

        resolved_norad_ids: list[int] = []
        group_id = row.get("group_id")
        if group_id is not None:
            cache_key = str(group_id)
            if cache_key not in group_cache:
                group_value = bind.execute(
                    sa.select(groups.c.satellite_ids).where(
                        sa.cast(groups.c.id, sa.String()) == cache_key
                    )
                ).scalar_one_or_none()
                group_cache[cache_key] = _normalize_norad_ids(group_value)
            resolved_norad_ids = group_cache[cache_key]

        bind.execute(
            sa.update(orbital_sources)
            .where(sa.cast(orbital_sources.c.id, sa.String()) == str(source_id))
            .values(norad_ids=resolved_norad_ids, query_mode="url")
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "orbital_sources" not in table_names:
        return

    source_columns = {column["name"] for column in inspector.get_columns("orbital_sources")}
    if "norad_ids" not in source_columns:
        return

    with op.batch_alter_table("orbital_sources", schema=None) as batch_op:
        batch_op.drop_column("norad_ids")
