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

"""Orbital source handlers."""

from typing import Any, Dict, Optional, Union

from crud import orbitalsources as orbital_sources_crud
from db import AsyncSessionLocal
from tlesync.state import sync_state_manager


async def get_orbital_sources(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Get all orbital sources."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug("Getting orbital sources")
        orbital_sources = await orbital_sources_crud.fetch_orbital_source(dbsession)
        return {"success": orbital_sources["success"], "data": orbital_sources.get("data", [])}


async def submit_orbital_source(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Add a new orbital source."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Adding orbital source, data: {data}")
        submit_reply = await orbital_sources_crud.add_orbital_source(dbsession, data)

        orbital_sources = await orbital_sources_crud.fetch_orbital_source(dbsession)
        return {
            "success": (orbital_sources["success"] & submit_reply["success"]),
            "data": orbital_sources.get("data", []),
        }


async def edit_orbital_source(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list, str]]:
    """Edit an existing orbital source."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Editing orbital source, data: {data}")
        if not data or "id" not in data:
            return {"success": False, "data": [], "error": "Missing orbital source ID"}

        edit_reply = await orbital_sources_crud.edit_orbital_source(dbsession, data["id"], data)

        orbital_sources = await orbital_sources_crud.fetch_orbital_source(dbsession)
        return {
            "success": (orbital_sources["success"] & edit_reply["success"]),
            "data": orbital_sources.get("data", []),
        }


async def delete_orbital_sources(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list, dict, str]]:
    """Delete orbital sources."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Deleting orbital source, data: {data}")
        delete_reply = await orbital_sources_crud.delete_orbital_sources(dbsession, data)

        orbital_sources = await orbital_sources_crud.fetch_orbital_source(dbsession)
        return {
            "success": (orbital_sources["success"] & delete_reply["success"]),
            "data": orbital_sources.get("data", []),
            "summary": delete_reply.get("deletion_summary", None),
            "message": delete_reply.get("data", None),
        }


async def fetch_sync_state(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, dict]]:
    """Get orbital synchronization state."""
    logger.debug("Getting orbital synchronization state")
    return {"success": True, "data": sync_state_manager.get_state()}


def register_handlers(registry):
    """Register orbital source handlers with command aliases for compatibility."""
    registry.register_batch(
        {
            # New command names.
            "get-orbital-sources": (get_orbital_sources, "data_request"),
            "submit-orbital-sources": (submit_orbital_source, "data_submission"),
            "edit-orbital-source": (edit_orbital_source, "data_submission"),
            "delete-orbital-sources": (delete_orbital_sources, "data_submission"),
            # Legacy command aliases.
            "get-tle-sources": (get_orbital_sources, "data_request"),
            "submit-tle-sources": (submit_orbital_source, "data_submission"),
            "edit-tle-source": (edit_orbital_source, "data_submission"),
            "delete-tle-sources": (delete_orbital_sources, "data_submission"),
            "fetch-sync-state": (fetch_sync_state, "data_request"),
        }
    )
