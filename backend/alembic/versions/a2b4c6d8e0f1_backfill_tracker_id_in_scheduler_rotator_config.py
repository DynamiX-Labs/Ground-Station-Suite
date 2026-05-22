"""backfill tracker_id in scheduler rotator hardware config

Revision ID: a2b4c6d8e0f1
Revises: 9d8f3d9aa2b7, fc7f37f92b40
Create Date: 2026-04-19 14:40:00.000000

"""

import json
import re
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b4c6d8e0f1"
down_revision: Union[str, Sequence[str], None] = ("9d8f3d9aa2b7", "fc7f37f92b40")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
TRACKING_STATE_PREFIX = "satellite-tracking:"
TARGET_ID_PATTERN = re.compile(r"^target-(\d+)$")


def _decode_json_dict(raw_value):
    if raw_value is None:
        return {}
    if isinstance(raw_value, dict):
        return dict(raw_value)
    if isinstance(raw_value, str):
        try:
            decoded = json.loads(raw_value)
            return decoded if isinstance(decoded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_tracker_id(candidate) -> str:
    if candidate is None:
        return ""
    tracker_id = str(candidate).strip()
    if not tracker_id or tracker_id.lower() == "none":
        return ""
    return tracker_id


def _normalize_rotator_id(candidate) -> str:
    if candidate is None:
        return ""
    rotator_id = str(candidate).strip()
    if not rotator_id or rotator_id.lower() == "none":
        return ""
    return rotator_id


def _extract_target_number(raw_tracker_id: str) -> int:
    tracker_id = str(raw_tracker_id or "").strip()
    matched = TARGET_ID_PATTERN.fullmatch(tracker_id)
    if not matched:
        return 0
    try:
        return int(matched.group(1))
    except (TypeError, ValueError):
        return 0


def _build_target_id(target_number: int) -> str:
    return f"target-{target_number}"


def _build_rotator_tracker_map(connection) -> tuple[dict[str, str], int]:
    mapping: dict[str, str] = {}
    max_target_number = 0
    rows = connection.exec_driver_sql(
        "SELECT name, value FROM tracking_state WHERE name LIKE ?",
        (f"{TRACKING_STATE_PREFIX}%",),
    ).fetchall()

    for name, value in rows:
        tracker_id = _normalize_tracker_id(str(name).replace(TRACKING_STATE_PREFIX, "", 1))
        target_number = _extract_target_number(tracker_id)
        if target_number <= 0:
            continue
        max_target_number = max(max_target_number, target_number)
        value_dict = _decode_json_dict(value)
        rotator_id = _normalize_rotator_id(value_dict.get("rotator_id"))
        if rotator_id and rotator_id not in mapping:
            mapping[rotator_id] = tracker_id

    return mapping, max_target_number + 1


def _backfill_table(
    connection, table_name: str, mapping: dict[str, str], next_target_number: int
) -> int:
    rows = connection.exec_driver_sql(
        f"SELECT id, rotator_id, hardware_config FROM {table_name}"
    ).fetchall()
    now_utc = datetime.now(timezone.utc)

    for row in rows:
        row_id = row[0]
        rotator_id = row[1]
        hardware_config = _decode_json_dict(row[2])
        if not isinstance(hardware_config, dict):
            continue

        rotator_config = hardware_config.get("rotator")
        if not isinstance(rotator_config, dict):
            rotator_config = {}

        tracker_id = _normalize_tracker_id(rotator_config.get("tracker_id"))
        if tracker_id:
            continue

        fallback_rotator_id = _normalize_rotator_id(rotator_config.get("id"))
        if not fallback_rotator_id:
            fallback_rotator_id = _normalize_rotator_id(rotator_id)
        if not fallback_rotator_id:
            continue

        resolved_tracker_id = mapping.get(fallback_rotator_id)
        if not resolved_tracker_id:
            resolved_tracker_id = _build_target_id(next_target_number)
            mapping[fallback_rotator_id] = resolved_tracker_id
            next_target_number += 1

        rotator_config["tracker_id"] = resolved_tracker_id

        hardware_config["rotator"] = rotator_config
        connection.exec_driver_sql(
            f"UPDATE {table_name} SET hardware_config = ?, updated_at = ? WHERE id = ?",
            (json.dumps(hardware_config), now_utc, row_id),
        )
    return next_target_number


def upgrade() -> None:
    connection = op.get_bind()
    mapping, next_target_number = _build_rotator_tracker_map(connection)
    next_target_number = _backfill_table(
        connection, "monitored_satellites", mapping, next_target_number
    )
    _backfill_table(connection, "scheduled_observations", mapping, next_target_number)


def downgrade() -> None:
    # Data backfill only; no schema change to reverse.
    pass
