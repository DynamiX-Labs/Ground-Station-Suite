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

"""Transmitter handlers."""

from typing import Any, Dict, Optional, Union

import crud
from db import AsyncSessionLocal
from tracker.runner import get_all_tracker_managers


async def submit_transmitter(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """
    Add a new transmitter.

    Args:
        sio: Socket.IO server instance
        data: Transmitter details including norad_cat_id
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and updated transmitters for the satellite
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Adding transmitter, data: {data}")
        add_reply = await crud.transmitters.add_transmitter(dbsession, data)
        norad_cat_id = None
        if add_reply.get("success"):
            norad_cat_id = (add_reply.get("data") or {}).get("norad_cat_id")
        if not norad_cat_id and data:
            norad_cat_id = data.get("norad_cat_id") or data.get("satelliteId")

        if not norad_cat_id:
            return {"success": add_reply.get("success", False), "data": []}

        transmitters = await crud.transmitters.fetch_transmitters_for_satellite(
            dbsession, norad_cat_id
        )
        if norad_cat_id:
            for manager in get_all_tracker_managers().values():
                await manager.notify_transmitters_changed(norad_cat_id)
        return {
            "success": (transmitters["success"] & add_reply["success"]),
            "data": transmitters.get("data", []),
        }


async def edit_transmitter(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """
    Edit an existing transmitter.

    Args:
        sio: Socket.IO server instance
        data: Transmitter ID and updated details
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and updated transmitters for the satellite
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Editing transmitter, data: {data}")
        transmitter_id = data.get("id") if data else None
        edit_reply = await crud.transmitters.edit_transmitter(dbsession, data)
        logger.info(edit_reply)
        norad_cat_id = None
        if edit_reply.get("success"):
            norad_cat_id = (edit_reply.get("data") or {}).get("norad_cat_id")
        if not norad_cat_id and data:
            norad_cat_id = data.get("norad_cat_id")
        if not norad_cat_id and transmitter_id:
            fetch_reply = await crud.transmitters.fetch_transmitter(dbsession, transmitter_id)
            norad_cat_id = (fetch_reply.get("data") or {}).get("norad_cat_id")
        transmitters = await crud.transmitters.fetch_transmitters_for_satellite(
            dbsession, norad_cat_id
        )
        if norad_cat_id:
            for manager in get_all_tracker_managers().values():
                await manager.notify_transmitters_changed(norad_cat_id)
        return {
            "success": (transmitters["success"] & edit_reply["success"]),
            "data": transmitters.get("data", []),
        }


async def delete_transmitter(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """
    Delete a transmitter.

    Args:
        sio: Socket.IO server instance
        data: Transmitter ID and norad_cat_id
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and updated transmitters for the satellite
    """
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Deleting transmitter, data: {data}")
        transmitter_id = data.get("transmitter_id") if data else None
        norad_cat_id = data.get("norad_cat_id") if data else None
        delete_reply = await crud.transmitters.delete_transmitter(dbsession, transmitter_id)
        transmitters = await crud.transmitters.fetch_transmitters_for_satellite(
            dbsession, norad_cat_id
        )
        if norad_cat_id:
            for manager in get_all_tracker_managers().values():
                await manager.notify_transmitters_changed(norad_cat_id)
        return {
            "success": (transmitters["success"] & delete_reply["success"]),
            "data": transmitters.get("data", []),
        }


def register_handlers(registry):
    """Register transmitter handlers with the command registry."""
    registry.register_batch(
        {
            "submit-transmitter": (submit_transmitter, "data_submission"),
            "edit-transmitter": (edit_transmitter, "data_submission"),
            "delete-transmitter": (delete_transmitter, "data_submission"),
        }
    )
