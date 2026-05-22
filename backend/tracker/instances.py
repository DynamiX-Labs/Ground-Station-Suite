# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from sqlalchemy import select

from common.constants import SocketEvents
from common.logger import logger
from db import AsyncSessionLocal
from db.models import TrackingState
from tracker.contracts import TRACKING_STATE_NAME_PREFIX
from tracker.runner import (
    assign_rotator_to_tracker,
    get_tracker_instances_payload,
    get_tracker_manager,
)


def _extract_tracker_id_from_state_name(name: str) -> str:
    prefix = f"{TRACKING_STATE_NAME_PREFIX}:"
    if not name or not name.startswith(prefix):
        return ""
    tracker_id = name[len(prefix) :].strip()
    if not tracker_id or tracker_id == "legacy-backup":
        return ""
    return tracker_id


async def restore_tracker_instances_from_db() -> list[str]:
    """Restore tracker runtimes/assignments from persisted tracker-scoped tracking_state rows."""
    restored_tracker_ids: list[str] = []
    prefix = f"{TRACKING_STATE_NAME_PREFIX}:%"

    async with AsyncSessionLocal() as dbsession:
        stmt = select(TrackingState).where(TrackingState.name.like(prefix))
        result = await dbsession.execute(stmt)
        rows = result.scalars().all()

    for row in rows:
        tracker_id = _extract_tracker_id_from_state_name(getattr(row, "name", ""))
        if not tracker_id:
            continue

        manager = get_tracker_manager(tracker_id)
        value = getattr(row, "value", {}) or {}
        if isinstance(value, dict):
            assign_rotator_to_tracker(tracker_id, value.get("rotator_id"))

        await manager.sync_tracking_state_from_db()
        restored_tracker_ids.append(tracker_id)

    if restored_tracker_ids:
        logger.info(
            "Restored %d tracker instance(s) from DB: %s",
            len(restored_tracker_ids),
            ", ".join(sorted(restored_tracker_ids)),
        )
    else:
        logger.info("No persisted tracker instances found to restore")

    return restored_tracker_ids


async def emit_tracker_instances(sio) -> None:
    """Emit tracker instance/ownership snapshot to all connected clients."""
    await sio.emit(SocketEvents.TRACKER_INSTANCES, get_tracker_instances_payload())
