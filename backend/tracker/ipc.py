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

"""IPC message types for tracker manager <-> tracker process communication."""

TRACKER_MSG_SET_TRACKING_STATE = "set_tracking_state"
TRACKER_MSG_SET_LOCATION = "set_location"
TRACKER_MSG_SET_HARDWARE = "set_hardware"
TRACKER_MSG_SET_TRANSMITTERS = "set_transmitters"
TRACKER_MSG_SET_SATELLITE_EPHEMERIS = "set_satellite_ephemeris"
TRACKER_MSG_SET_MAP_SETTINGS = "set_map_settings"
TRACKER_MSG_COMMAND = "command"


def build_tracker_message(msg_type: str, payload: dict) -> dict:
    """Build a tracker IPC message with a consistent shape."""
    return {"type": msg_type, "payload": payload}
