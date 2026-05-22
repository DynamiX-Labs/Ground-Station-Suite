"""migrate legacy tracking_state to tracker keys

Revision ID: 9d8f3d9aa2b7
Revises: d1e2f3a4b5c6
Create Date: 2026-04-19 12:49:03.845384

"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d8f3d9aa2b7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_NAME = "satellite-tracking"
BACKUP_NAME = "satellite-tracking:legacy-backup"
PREFIX = "satellite-tracking:"
TARGET_ID_PATTERN = re.compile(r"^target-(\d+)$")


def _normalize_rotator_id(candidate) -> str:
    if candidate is None:
        return ""
    rotator_id = str(candidate).strip()
    if not rotator_id or rotator_id.lower() == "none":
        return ""
    return rotator_id


def _decode_value(raw_value):
    if raw_value is None:
        return {}
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        try:
            decoded = json.loads(raw_value)
            return decoded if isinstance(decoded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_tracker_name(raw_name) -> str:
    if not raw_name:
        return ""
    name = str(raw_name).strip()
    if not name.startswith(PREFIX):
        return ""
    return name[len(PREFIX) :]


def _extract_target_number(raw_tracker_id: str) -> int:
    tracker_id = str(raw_tracker_id or "").strip()
    matched = TARGET_ID_PATTERN.fullmatch(tracker_id)
    if not matched:
        return 0
    try:
        return int(matched.group(1))
    except (TypeError, ValueError):
        return 0


def _resolve_tracker_state_name(connection, rotator_id: str) -> str:
    rows = connection.exec_driver_sql(
        "SELECT name, value FROM tracking_state WHERE name LIKE ?",
        (f"{PREFIX}%",),
    ).fetchall()

    max_target_number = 0
    for row in rows:
        tracker_id = _normalize_tracker_name(row[0])
        max_target_number = max(max_target_number, _extract_target_number(tracker_id))
        value = _decode_value(row[1])
        if _normalize_rotator_id(value.get("rotator_id")) != rotator_id:
            continue
        target_number = _extract_target_number(tracker_id)
        if target_number > 0:
            return f"{PREFIX}{tracker_id}"

    return f"{PREFIX}target-{max_target_number + 1}"


def upgrade() -> None:
    connection = op.get_bind()
    legacy_row = connection.exec_driver_sql(
        "SELECT id, name, value FROM tracking_state WHERE name = ? LIMIT 1",
        (LEGACY_NAME,),
    ).first()
    if not legacy_row:
        return

    legacy_id = legacy_row[0]
    legacy_value = _decode_value(legacy_row[2])
    rotator_id = _normalize_rotator_id(legacy_value.get("rotator_id"))

    if rotator_id:
        tracker_state_name = _resolve_tracker_state_name(connection, rotator_id)
        tracker_row = connection.exec_driver_sql(
            "SELECT id, value FROM tracking_state WHERE name = ? LIMIT 1",
            (tracker_state_name,),
        ).first()
        now_utc = datetime.now(timezone.utc)

        if tracker_row:
            tracker_id = tracker_row[0]
            existing_value = _decode_value(tracker_row[1])
            merged_value = {**legacy_value, **existing_value}
            if merged_value != existing_value:
                connection.exec_driver_sql(
                    "UPDATE tracking_state SET value = ?, updated = ? WHERE id = ?",
                    (json.dumps(merged_value), now_utc, tracker_id),
                )
        else:
            connection.exec_driver_sql(
                "INSERT INTO tracking_state (id, name, value, added, updated) VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, tracker_state_name, json.dumps(legacy_value), now_utc, now_utc),
            )

    backup_row = connection.exec_driver_sql(
        "SELECT id FROM tracking_state WHERE name = ? LIMIT 1",
        (BACKUP_NAME,),
    ).first()

    if backup_row:
        connection.exec_driver_sql("DELETE FROM tracking_state WHERE id = ?", (legacy_id,))
    else:
        connection.exec_driver_sql(
            "UPDATE tracking_state SET name = ?, updated = ? WHERE id = ?",
            (BACKUP_NAME, datetime.now(timezone.utc), legacy_id),
        )


def downgrade() -> None:
    connection = op.get_bind()
    legacy_row = connection.exec_driver_sql(
        "SELECT id FROM tracking_state WHERE name = ? LIMIT 1",
        (LEGACY_NAME,),
    ).first()
    backup_row = connection.exec_driver_sql(
        "SELECT id FROM tracking_state WHERE name = ? LIMIT 1",
        (BACKUP_NAME,),
    ).first()

    if backup_row and not legacy_row:
        connection.exec_driver_sql(
            "UPDATE tracking_state SET name = ?, updated = ? WHERE id = ?",
            (LEGACY_NAME, datetime.now(timezone.utc), backup_row[0]),
        )
