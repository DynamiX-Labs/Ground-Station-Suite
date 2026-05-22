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

"""
State manager for satellite tracking.
Handles state change detection, validation, and command processing.
"""

import logging
from typing import Any, List, Tuple

from common.constants import DictKeys, SocketEvents, TrackerCommands, TrackingEvents
from tracker.ipc import TRACKER_MSG_COMMAND

logger = logging.getLogger("tracker-worker")


class StateManager:
    """Handles state management and validation for satellite tracking."""

    def __init__(self, tracker):
        """
        Initialize the state manager.

        :param tracker: Reference to the parent SatelliteTracker instance
        """
        self.tracker = tracker

    @staticmethod
    def _fmt_state_value(value: Any) -> Any:
        """Normalize null-ish state values for human-readable logs."""
        return "none" if value is None else value

    def check_state_changes(self) -> List[Tuple[str, Any, Any]]:
        """Check for state changes and return list of changes."""
        changes: List[Tuple[str, Any, Any]] = []

        if self.tracker.current_norad_id != self.tracker.prev_norad_id:
            changes.append(("satellite", self.tracker.prev_norad_id, self.tracker.current_norad_id))
            self.tracker.prev_norad_id = self.tracker.current_norad_id

        if self.tracker.current_rotator_state != self.tracker.prev_rotator_state:
            changes.append(
                (
                    "rotator_state",
                    self.tracker.prev_rotator_state,
                    self.tracker.current_rotator_state,
                )
            )
            self.tracker.prev_rotator_state = self.tracker.current_rotator_state

        if self.tracker.current_rotator_id != self.tracker.prev_rotator_id:
            changes.append(
                ("rotator_id", self.tracker.prev_rotator_id, self.tracker.current_rotator_id)
            )
            self.tracker.prev_rotator_id = self.tracker.current_rotator_id

        if self.tracker.current_rig_state != self.tracker.prev_rig_state:
            changes.append(
                ("rig_state", self.tracker.prev_rig_state, self.tracker.current_rig_state)
            )
            self.tracker.prev_rig_state = self.tracker.current_rig_state

        if self.tracker.current_transmitter_id != self.tracker.prev_transmitter_id:
            changes.append(
                (
                    "transmitter_id",
                    self.tracker.prev_transmitter_id,
                    self.tracker.current_transmitter_id,
                )
            )
            self.tracker.prev_transmitter_id = self.tracker.current_transmitter_id

        if self.tracker.current_rig_id != self.tracker.prev_rig_id:
            changes.append(("rig_id", self.tracker.prev_rig_id, self.tracker.current_rig_id))
            self.tracker.prev_rig_id = self.tracker.current_rig_id

        return changes

    async def process_state_changes(self, changes: List[Tuple[str, Any, Any]]):
        """Process all detected state changes."""
        for change_type, old, new in changes:
            if change_type == "satellite":
                await self.handle_satellite_change(old, new)
            elif change_type == "rotator_state":
                await self.tracker.rotator_handler.handle_rotator_state_change(old, new)
            elif change_type == "rotator_id":
                await self.handle_rotator_id_change(old, new)
            elif change_type == "rig_state":
                await self.tracker.rig_handler.handle_rig_state_change(old, new)
            elif change_type == "transmitter_id":
                await self.handle_transmitter_id_change(old, new)
            elif change_type == "rig_id":
                await self.handle_rig_id_change(old, new)

    async def handle_satellite_change(self, old, new):
        """Handle satellite target change events."""
        sat_name = self.tracker.satellite_data.get("details", {}).get("name", "Unknown")
        logger.info(
            "Target satellite change detected from '%s' to '%s' (%s)",
            self._fmt_state_value(old),
            self._fmt_state_value(new),
            sat_name,
        )

        # Reset state
        self.tracker.rotator_data["minelevation"] = False
        self.tracker.rotator_data["maxelevation"] = False
        self.tracker.rotator_data["minazimuth"] = False
        self.tracker.rotator_data["maxazimuth"] = False
        self.tracker.notified = {}

        # Notify about change
        self.tracker.queue_out.put(
            {
                DictKeys.EVENT: SocketEvents.SATELLITE_TRACKING,
                DictKeys.DATA: {
                    DictKeys.EVENTS: [
                        {DictKeys.NAME: TrackingEvents.NORAD_ID_CHANGE, "old": old, "new": new}
                    ],
                    DictKeys.DATA: self.tracker.satellite_data,
                },
            }
        )

        # Update rig state in database
        updated_tracking_state = dict(self.tracker.input_tracking_state or {})
        updated_tracking_state["transmitter_id"] = "none"
        updated_tracking_state["rig_state"] = (
            "stopped"
            if self.tracker.current_rig_state == "tracking"
            else self.tracker.current_rig_state
        )
        self.tracker.input_tracking_state = updated_tracking_state

        # Update local state
        self.tracker.rig_data["tracking"] = False
        self.tracker.rig_data["stopped"] = True

        # Send updated rig_data and tracking_state to trigger VFO unlock
        self.tracker.queue_out.put(
            {
                DictKeys.EVENT: SocketEvents.SATELLITE_TRACKING,
                DictKeys.DATA: {
                    DictKeys.RIG_DATA: self.tracker.rig_data.copy(),
                    DictKeys.TRACKING_STATE: updated_tracking_state,
                },
            }
        )

    async def handle_rotator_id_change(self, old, new):
        """Handle rotator ID changes."""
        logger.info(
            "Rotator ID change detected from '%s' to '%s'",
            self._fmt_state_value(old),
            self._fmt_state_value(new),
        )

    async def handle_transmitter_id_change(self, old, new):
        """Handle transmitter ID changes."""
        logger.info(
            "Transmitter ID change detected from '%s' to '%s'",
            self._fmt_state_value(old),
            self._fmt_state_value(new),
        )

    async def handle_rig_id_change(self, old, new):
        """Handle rig ID changes."""
        logger.info(
            "Rig ID change detected from '%s' to '%s'",
            self._fmt_state_value(old),
            self._fmt_state_value(new),
        )

    async def process_commands(self) -> bool:
        """
        Process incoming commands from the queue.

        :return: True if should stop, False otherwise
        """
        try:
            while not self.tracker.queue_in.empty():
                command = self.tracker.queue_in.get_nowait()
                logger.debug(f"Received command: {command}")

                if command.get("type"):
                    if command.get("type") == TRACKER_MSG_COMMAND:
                        cmd_payload = command.get("payload", {})
                        cmd_type = cmd_payload.get("command")
                    else:
                        self.tracker.apply_input_message(command)
                        continue
                else:
                    cmd_type = command.get("command")

                if cmd_type == TrackerCommands.STOP:
                    logger.info("Received stop command, exiting tracking task")
                    return True
                elif cmd_type == TrackerCommands.NUDGE_CLOCKWISE:
                    self.tracker.nudge_offset["az"] += 2
                elif cmd_type == TrackerCommands.NUDGE_COUNTER_CLOCKWISE:
                    self.tracker.nudge_offset["az"] -= 2
                elif cmd_type == TrackerCommands.NUDGE_UP:
                    self.tracker.nudge_offset["el"] += 2
                elif cmd_type == TrackerCommands.NUDGE_DOWN:
                    self.tracker.nudge_offset["el"] -= 2

        except Exception as e:
            logger.error(f"Error processing commands: {e}")

        return False  # Continue running

    async def validate_hardware_states(self):
        """Validate that hardware states match database expectations."""
        # Check if rotator should be connected but isn't
        if (
            self.tracker.current_rotator_state == "connected"
            and self.tracker.rotator_controller is None
        ):
            logger.warning("Tracking state said rotator must be connected but it is not")
            updated_tracking_state = dict(self.tracker.input_tracking_state or {})
            updated_tracking_state["rotator_state"] = "disconnected"
            self.tracker.input_tracking_state = updated_tracking_state

            self.tracker.rotator_data["connected"] = False
            self.tracker.rotator_data["tracking"] = False
            self.tracker.rotator_data["stopped"] = True

            self.tracker.queue_out.put(
                {
                    DictKeys.EVENT: SocketEvents.SATELLITE_TRACKING,
                    DictKeys.DATA: {
                        DictKeys.ROTATOR_DATA: self.tracker.rotator_data.copy(),
                        DictKeys.TRACKING_STATE: updated_tracking_state,
                    },
                }
            )

        # Check if rig should be connected but isn't
        if self.tracker.current_rig_state == "connected" and self.tracker.rig_controller is None:
            logger.warning("Tracking state said rig must be connected but it is not")
            updated_tracking_state = dict(self.tracker.input_tracking_state or {})
            updated_tracking_state["rig_state"] = "disconnected"
            self.tracker.input_tracking_state = updated_tracking_state

            self.tracker.rig_data["connected"] = False
            self.tracker.rig_data["tracking"] = False
            self.tracker.rig_data["stopped"] = True

            self.tracker.queue_out.put(
                {
                    DictKeys.EVENT: SocketEvents.SATELLITE_TRACKING,
                    DictKeys.DATA: {
                        DictKeys.RIG_DATA: self.tracker.rig_data.copy(),
                        DictKeys.TRACKING_STATE: updated_tracking_state,
                    },
                }
            )

    def cleanup_data_states(self):
        """Clean up temporary state flags."""
        # Clean up rotator_data
        self.tracker.rotator_data["error"] = False
        # Note: outofbounds, minelevation, maxelevation, minazimuth, maxazimuth
        # are NOT reset here - they persist until next position check

        # Clean up rig_data
        self.tracker.rig_data["tuning"] = False
        self.tracker.rig_data["error"] = False

        # Reset nudge offset values
        self.tracker.nudge_offset = {"az": 0, "el": 0}
