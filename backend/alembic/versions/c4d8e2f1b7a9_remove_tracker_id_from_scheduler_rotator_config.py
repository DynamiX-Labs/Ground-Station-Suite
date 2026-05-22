"""remove tracker_id from scheduler rotator hardware config

Revision ID: c4d8e2f1b7a9
Revises: b3f7a9c2d1e4
Create Date: 2026-04-24 13:10:00.000000

"""

import json
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8e2f1b7a9"
down_revision: Union[str, Sequence[str], None] = "b3f7a9c2d1e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


def _strip_legacy_tracker_ids(connection, table_name: str) -> None:
    rows = connection.exec_driver_sql(f"SELECT id, hardware_config FROM {table_name}").fetchall()
    now_utc = datetime.now(timezone.utc)

    for row_id, raw_hardware_config in rows:
        hardware_config = _decode_json_dict(raw_hardware_config)
        if not isinstance(hardware_config, dict):
            continue

        rotator_config = hardware_config.get("rotator")
        if not isinstance(rotator_config, dict):
            continue

        if "tracker_id" not in rotator_config:
            continue

        rotator_config = dict(rotator_config)
        rotator_config.pop("tracker_id", None)
        hardware_config["rotator"] = rotator_config

        connection.exec_driver_sql(
            f"UPDATE {table_name} SET hardware_config = ?, updated_at = ? WHERE id = ?",
            (json.dumps(hardware_config), now_utc, row_id),
        )


def upgrade() -> None:
    connection = op.get_bind()
    _strip_legacy_tracker_ids(connection, "monitored_satellites")
    _strip_legacy_tracker_ids(connection, "scheduled_observations")


def downgrade() -> None:
    # Data cleanup only; removed legacy tracker ids cannot be reconstructed safely.
    pass
