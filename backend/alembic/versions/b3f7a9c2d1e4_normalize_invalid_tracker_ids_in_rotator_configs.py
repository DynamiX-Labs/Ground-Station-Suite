"""normalize invalid tracker_id values in rotator hardware config

Revision ID: b3f7a9c2d1e4
Revises: a2b4c6d8e0f1
Create Date: 2026-04-24 09:15:00.000000

"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f7a9c2d1e4"
down_revision: Union[str, Sequence[str], None] = "a2b4c6d8e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TRACKING_STATE_PREFIX = "satellite-tracking:"
TARGET_ID_PATTERN = re.compile(r"^target-([1-9][0-9]*)$")
LEGACY_TRACKING_STATE_NAME = "satellite-tracking"
LEGACY_BACKUP_TRACKING_STATE_NAME = "satellite-tracking:legacy-backup"


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


def _is_valid_target_tracker_id(candidate) -> bool:
    tracker_id = _normalize_tracker_id(candidate)
    return bool(TARGET_ID_PATTERN.fullmatch(tracker_id))


def _extract_target_number(raw_tracker_id: str) -> int:
    tracker_id = _normalize_tracker_id(raw_tracker_id)
    matched = TARGET_ID_PATTERN.fullmatch(tracker_id)
    if not matched:
        return 0
    try:
        return int(matched.group(1))
    except (TypeError, ValueError):
        return 0


def _build_target_id(target_number: int) -> str:
    return f"target-{target_number}"


def _register_mapping(mapping: dict[str, str], rotator_id: str, tracker_id: str) -> int:
    if not rotator_id or not _is_valid_target_tracker_id(tracker_id):
        return 0
    existing = mapping.get(rotator_id)
    if existing and _extract_target_number(existing) > 0:
        return _extract_target_number(existing)
    mapping[rotator_id] = tracker_id
    return _extract_target_number(tracker_id)


def _build_rotator_tracker_map(connection) -> tuple[dict[str, str], int]:
    mapping: dict[str, str] = {}
    max_target_number = 0

    tracking_rows = connection.exec_driver_sql(
        "SELECT name, value FROM tracking_state WHERE name LIKE ?",
        (f"{TRACKING_STATE_PREFIX}%",),
    ).fetchall()

    for name, value in tracking_rows:
        tracker_name = str(name or "")
        if not tracker_name.startswith(TRACKING_STATE_PREFIX):
            continue
        tracker_id = _normalize_tracker_id(tracker_name.replace(TRACKING_STATE_PREFIX, "", 1))
        value_dict = _decode_json_dict(value)
        rotator_id = _normalize_rotator_id(value_dict.get("rotator_id"))
        max_target_number = max(max_target_number, _extract_target_number(tracker_id))
        max_target_number = max(
            max_target_number,
            _register_mapping(mapping, rotator_id, tracker_id),
        )

    for table_name in ("monitored_satellites", "scheduled_observations"):
        rows = connection.exec_driver_sql(
            f"SELECT rotator_id, hardware_config FROM {table_name}"
        ).fetchall()
        for rotator_id, hardware_config in rows:
            hardware = _decode_json_dict(hardware_config)
            rotator_cfg = hardware.get("rotator") if isinstance(hardware, dict) else {}
            if not isinstance(rotator_cfg, dict):
                rotator_cfg = {}
            tracker_id = _normalize_tracker_id(rotator_cfg.get("tracker_id"))
            if not _is_valid_target_tracker_id(tracker_id):
                continue
            resolved_rotator_id = _normalize_rotator_id(rotator_cfg.get("id"))
            if not resolved_rotator_id:
                resolved_rotator_id = _normalize_rotator_id(rotator_id)
            max_target_number = max(
                max_target_number,
                _register_mapping(mapping, resolved_rotator_id, tracker_id),
            )

    return mapping, max_target_number + 1


def _ensure_tracker_state_rows(
    connection,
    mapping: dict[str, str],
    legacy_value_by_rotator: dict[str, dict],
) -> None:
    now_utc = datetime.now(timezone.utc)
    for rotator_id, tracker_id in mapping.items():
        tracking_state_name = f"{TRACKING_STATE_PREFIX}{tracker_id}"
        existing = connection.exec_driver_sql(
            "SELECT id FROM tracking_state WHERE name = ? LIMIT 1",
            (tracking_state_name,),
        ).first()
        if existing:
            continue

        initial_value = legacy_value_by_rotator.get(rotator_id) or {
            "rotator_id": rotator_id,
            "rotator_state": "disconnected",
            "rig_state": "disconnected",
            "rig_id": "none",
            "transmitter_id": "none",
        }

        connection.exec_driver_sql(
            "INSERT INTO tracking_state (id, name, value, added, updated) VALUES (?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, tracking_state_name, json.dumps(initial_value), now_utc, now_utc),
        )


def _normalize_legacy_tracking_state(
    connection, mapping: dict[str, str], next_target_number: int
) -> int:
    legacy_row = connection.exec_driver_sql(
        "SELECT id, value FROM tracking_state WHERE name = ? LIMIT 1",
        (LEGACY_TRACKING_STATE_NAME,),
    ).first()
    if not legacy_row:
        return next_target_number

    legacy_id = legacy_row[0]
    legacy_value = _decode_json_dict(legacy_row[1])
    legacy_rotator_id = _normalize_rotator_id(legacy_value.get("rotator_id"))
    if legacy_rotator_id and legacy_rotator_id not in mapping:
        mapping[legacy_rotator_id] = _build_target_id(next_target_number)
        next_target_number += 1

    backup_row = connection.exec_driver_sql(
        "SELECT id FROM tracking_state WHERE name = ? LIMIT 1",
        (LEGACY_BACKUP_TRACKING_STATE_NAME,),
    ).first()
    now_utc = datetime.now(timezone.utc)
    if backup_row:
        connection.exec_driver_sql("DELETE FROM tracking_state WHERE id = ?", (legacy_id,))
    else:
        connection.exec_driver_sql(
            "UPDATE tracking_state SET name = ?, updated = ? WHERE id = ?",
            (LEGACY_BACKUP_TRACKING_STATE_NAME, now_utc, legacy_id),
        )

    return next_target_number


def _backfill_table(
    connection, table_name: str, mapping: dict[str, str], next_target_number: int
) -> int:
    rows = connection.exec_driver_sql(
        f"SELECT id, rotator_id, hardware_config FROM {table_name}"
    ).fetchall()
    now_utc = datetime.now(timezone.utc)

    for row_id, row_rotator_id, raw_hardware_config in rows:
        hardware_config = _decode_json_dict(raw_hardware_config)
        if not isinstance(hardware_config, dict):
            continue

        rotator_config = hardware_config.get("rotator")
        if not isinstance(rotator_config, dict):
            continue

        resolved_rotator_id = _normalize_rotator_id(rotator_config.get("id"))
        if not resolved_rotator_id:
            resolved_rotator_id = _normalize_rotator_id(row_rotator_id)
        if not resolved_rotator_id:
            continue

        current_tracker_id = _normalize_tracker_id(rotator_config.get("tracker_id"))
        resolved_tracker_id = mapping.get(resolved_rotator_id)
        if not resolved_tracker_id:
            if _is_valid_target_tracker_id(current_tracker_id):
                resolved_tracker_id = current_tracker_id
                mapping[resolved_rotator_id] = resolved_tracker_id
            else:
                resolved_tracker_id = _build_target_id(next_target_number)
                mapping[resolved_rotator_id] = resolved_tracker_id
                next_target_number += 1

        if current_tracker_id == resolved_tracker_id:
            continue

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
    next_target_number = _normalize_legacy_tracking_state(connection, mapping, next_target_number)
    legacy_value_by_rotator: dict[str, dict] = {}
    legacy_backup_row = connection.exec_driver_sql(
        "SELECT value FROM tracking_state WHERE name = ? LIMIT 1",
        (LEGACY_BACKUP_TRACKING_STATE_NAME,),
    ).first()
    if legacy_backup_row:
        legacy_value = _decode_json_dict(legacy_backup_row[0])
        legacy_rotator_id = _normalize_rotator_id(legacy_value.get("rotator_id"))
        if legacy_rotator_id:
            legacy_value_by_rotator[legacy_rotator_id] = legacy_value
    _ensure_tracker_state_rows(connection, mapping, legacy_value_by_rotator)
    next_target_number = _backfill_table(
        connection, "monitored_satellites", mapping, next_target_number
    )
    next_target_number = _backfill_table(
        connection, "scheduled_observations", mapping, next_target_number
    )
    _ensure_tracker_state_rows(connection, mapping, legacy_value_by_rotator)


def downgrade() -> None:
    # Data normalization only; no schema changes to reverse.
    pass
