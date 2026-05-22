# Copyright (c) 2026 Efstratios Goudelis
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

"""Shared tracker-state update helpers with rotator ownership arbitration."""

from typing import Any, Dict, Optional

from tracker.contracts import require_tracker_id
from tracker.runner import (
    assign_rotator_to_tracker,
    get_assigned_rotator_for_tracker,
    get_tracker_manager,
    restore_tracker_rotator_assignment,
)


async def update_tracking_state_with_ownership(
    tracker_id: str, value: Dict[str, Any], requester_sid: Optional[str] = None
) -> Dict[str, Any]:
    """Update tracker state while enforcing one-rotator-per-tracker ownership."""
    normalized_tracker_id = require_tracker_id(tracker_id)
    payload = dict(value or {})

    assignment_previous_rotator = get_assigned_rotator_for_tracker(normalized_tracker_id)
    requested_rotator_id = payload.get("rotator_id")
    ownership_touched = requested_rotator_id is not None

    if ownership_touched:
        assignment_result = assign_rotator_to_tracker(normalized_tracker_id, requested_rotator_id)
        if not assignment_result.get("success"):
            owner_tracker_id = assignment_result.get("owner_tracker_id")
            return {
                "success": False,
                "error": "rotator_in_use",
                "message": (
                    f"Rotator '{requested_rotator_id}' is already assigned to tracker "
                    f"'{owner_tracker_id}'."
                ),
                "data": {
                    "tracker_id": normalized_tracker_id,
                    "rotator_id": requested_rotator_id,
                    "owner_tracker_id": owner_tracker_id,
                },
            }

    manager = get_tracker_manager(normalized_tracker_id)
    result = await manager.update_tracking_state(requester_sid=requester_sid, **payload)

    if not result.get("success") and ownership_touched:
        restore_tracker_rotator_assignment(normalized_tracker_id, assignment_previous_rotator)

    response: Dict[str, Any] = {
        "success": bool(result.get("success")),
        "result": result,
    }
    if not result.get("success"):
        response["error"] = result.get("error", "tracking_state_update_failed")
    return response
