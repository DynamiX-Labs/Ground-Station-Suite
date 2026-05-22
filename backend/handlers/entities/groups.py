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

"""Satellite group handlers."""

from typing import Any, Dict, Optional, Union

import crud
from db import AsyncSessionLocal
from db.models import SatelliteGroupType
from tracking.events import fetch_next_events_for_group


async def get_satellite_groups(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """
    Get all satellite groups.

    Args:
        sio: Socket.IO server instance
        data: Not used
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and satellite groups
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Getting satellite groups, data: {data}")
        satellite_groups = await crud.groups.fetch_satellite_group(dbsession)
        return {
            "success": satellite_groups["success"],
            "data": satellite_groups.get("data", []),
        }


async def get_satellite_groups_user(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """
    Get user-created satellite groups only.

    Args:
        sio: Socket.IO server instance
        data: Not used
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and user satellite groups
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Getting user satellite groups, data: {data}")
        satellite_groups = await crud.groups.fetch_satellite_group(dbsession)
        groups_data = satellite_groups.get("data") or []

        # Only return the user groups
        filtered_groups = [
            satellite_group
            for satellite_group in groups_data
            if satellite_group["type"] == SatelliteGroupType.USER
        ]

        return {"success": satellite_groups["success"], "data": filtered_groups}


async def get_satellite_groups_system(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """
    Get system-created satellite groups only.

    Args:
        sio: Socket.IO server instance
        data: Not used
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and system satellite groups
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Getting system satellite groups, data: {data}")
        satellite_groups = await crud.groups.fetch_satellite_group(dbsession)
        groups_data = satellite_groups.get("data") or []

        # Only return the system groups
        filtered_groups = [
            satellite_group
            for satellite_group in groups_data
            if satellite_group["type"] == SatelliteGroupType.SYSTEM
        ]
        return {"success": satellite_groups["success"], "data": filtered_groups}


async def submit_satellite_group(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """
    Add a new satellite group.

    Args:
        sio: Socket.IO server instance
        data: Satellite group details
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and updated satellite groups
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Adding satellite group, data: {data}")
        submit_reply = await crud.groups.add_satellite_group(dbsession, data)

        satellite_groups = await crud.groups.fetch_satellite_group(dbsession, group_type="user")
        return {
            "success": (satellite_groups["success"] & submit_reply["success"]),
            "data": satellite_groups.get("data", []),
        }


async def edit_satellite_group(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list, str]]:
    """
    Edit an existing satellite group.

    Args:
        sio: Socket.IO server instance
        data: Satellite group ID and updated details
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and updated satellite groups
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Editing satellite group, data: {data}")
        if not data or "id" not in data:
            return {"success": False, "data": [], "error": "Missing satellite group ID"}

        edit_reply = await crud.groups.edit_satellite_group(dbsession, data["id"], data)

        satellite_groups = await crud.groups.fetch_satellite_group(dbsession, group_type="user")
        return {
            "success": (satellite_groups["success"] & edit_reply["success"]),
            "data": satellite_groups.get("data", []),
        }


async def delete_satellite_group(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """
    Delete satellite groups.

    Args:
        sio: Socket.IO server instance
        data: List of satellite group IDs to delete
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and updated satellite groups
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Deleting satellite groups, data: {data}")
        delete_reply = await crud.groups.delete_satellite_group(dbsession, data)

        satellite_groups = await crud.groups.fetch_satellite_group(dbsession, group_type="user")
        return {
            "success": (satellite_groups["success"] & delete_reply["success"]),
            "data": satellite_groups.get("data", []),
        }


async def fetch_next_passes_for_group(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list, float]]:
    """
    Fetch next passes for a satellite group.

    Args:
        sio: Socket.IO server instance
        data: Group ID, forecast hours, and optional force_recalculate flag
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and next passes
    """
    group_id = data.get("group_id", None) if data else None
    hours = data.get("hours", 2.0) if data else 2.0
    force_recalculate = data.get("force_recalculate", False) if data else False
    logger.info(
        f"Handling request from client_id={sid}, group_id={group_id}, hours={hours}, "
        f"force_recalculate={force_recalculate} (get_next_passes_for_group)"
    )
    next_passes = await fetch_next_events_for_group(
        group_id=group_id, hours=hours, force_recalculate=force_recalculate
    )
    return {
        "success": next_passes["success"],
        "data": next_passes.get("data", []),
        "cached": next_passes.get("cached", False),
        "forecast_hours": next_passes.get("forecast_hours", 4.0),
        "pass_range_start": next_passes.get("pass_range_start"),
        "pass_range_end": next_passes.get("pass_range_end"),
    }


def register_handlers(registry):
    """Register satellite group handlers with the command registry."""
    registry.register_batch(
        {
            "get-satellite-groups": (get_satellite_groups, "data_request"),
            "get-satellite-groups-user": (get_satellite_groups_user, "data_request"),
            "get-satellite-groups-system": (get_satellite_groups_system, "data_request"),
            "submit-satellite-group": (submit_satellite_group, "data_submission"),
            "edit-satellite-group": (edit_satellite_group, "data_submission"),
            "delete-satellite-group": (delete_satellite_group, "data_submission"),
            "fetch-next-passes-for-group": (fetch_next_passes_for_group, "data_request"),
        }
    )
