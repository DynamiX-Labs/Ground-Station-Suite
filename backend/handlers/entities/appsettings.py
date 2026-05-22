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

"""Application configuration handlers."""

from typing import Any, Dict, Optional, Union

from common.appsettings import app_settings_service


async def get_app_config(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, dict, str]]:
    """Return schema and effective application config values for UI editing."""
    del sio, data, sid  # handler signature is fixed by dispatcher
    logger.debug("Fetching app config settings payload")
    return {"success": True, "data": app_settings_service.get_payload()}


async def update_app_config(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, dict, str]]:
    """Validate and persist app config updates."""
    del sio, sid
    payload = data or {}
    if isinstance(payload, dict) and isinstance(payload.get("values"), dict):
        updates = payload["values"]
    elif isinstance(payload, dict):
        updates = payload
    else:
        updates = {}
    logger.debug("Updating app config settings, keys=%s", sorted(list(updates.keys())))
    result = app_settings_service.update(updates)
    if result.get("success"):
        return {"success": True, "data": result.get("data", {})}
    return {
        "success": False,
        "error": result.get("error", "Unknown error"),
        "data": result.get("data"),
    }


def register_handlers(registry):
    """Register app settings handlers with the command registry."""
    registry.register_batch(
        {
            "get-app-config": (get_app_config, "data_request"),
            "update-app-config": (update_app_config, "data_submission"),
        }
    )
