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

"""System information handlers."""

from typing import Any, Dict, Optional

from server.libraryinfo import get_frontend_library_versions, get_library_versions


async def fetch_library_versions(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Any]:
    """
    Fetch all library versions and metadata.

    Args:
        sio: Socket.IO server instance
        data: Not used
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and library versions
    """
    logger.debug("Fetching library versions")
    try:
        library_info = get_library_versions()
        return {"success": True, "data": library_info}
    except Exception as e:
        logger.error(f"Error fetching library versions: {e}")
        return {"success": False, "error": str(e)}


async def fetch_frontend_library_versions(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Any]:
    """
    Fetch all frontend library versions from package.json.

    Args:
        sio: Socket.IO server instance
        data: Not used
        logger: Logger instance
        sid: Socket.IO session ID

    Returns:
        Dictionary with success status and frontend library versions
    """
    logger.debug("Fetching frontend library versions")
    try:
        library_info = get_frontend_library_versions()
        return {"success": True, "data": library_info}
    except Exception as e:
        logger.error(f"Error fetching frontend library versions: {e}")
        return {"success": False, "error": str(e)}


def register_handlers(registry):
    """Register system info handlers with the command registry."""
    registry.register_batch(
        {
            "fetch_library_versions": (fetch_library_versions, "data_request"),
            "fetch_frontend_library_versions": (
                fetch_frontend_library_versions,
                "data_request",
            ),
        }
    )
