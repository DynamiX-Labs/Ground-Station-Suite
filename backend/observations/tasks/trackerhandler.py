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

"""Tracker task handler - manages rotator tracking lifecycle."""

import asyncio
import traceback
from typing import Any, Dict, List, Optional

from common.logger import logger
from crud import trackingstate as trackingstate_crud
from db import AsyncSessionLocal
from tracker.contracts import get_tracking_state_name
from tracker.instances import emit_tracker_instances
from tracker.runner import (
    create_observation_tracker_slot,
    get_assigned_tracker_for_rotator,
    get_tracker_manager,
    remove_tracker_instance,
)
from tracker.stateupdate import update_tracking_state_with_ownership


class TrackerHandler:
    """Handles rotator tracking lifecycle for observations."""

    def __init__(self, sio: Optional[Any] = None):
        self.sio = sio

    async def _emit_tracker_instances_snapshot(self) -> None:
        if self.sio is None:
            return
        try:
            await emit_tracker_instances(self.sio)
        except Exception as exc:
            logger.warning("Failed to emit tracker instance snapshot: %s", exc)

    @staticmethod
    def _extract_transmitter_id(tasks: List[Dict[str, Any]]) -> str:
        """Extract transmitter ID from decoder tasks (if any)."""
        for task in tasks:
            if task.get("type") == "decoder":
                return str(task.get("config", {}).get("transmitter_id", "none"))
        return "none"

    async def _remove_observation_tracker_instance(self, tracker_id: str) -> bool:
        """
        Remove an observation-owned tracker runtime and its persisted tracking state row.

        Used for ephemeral tracker slots created for observations without rotator ownership.
        """
        try:
            remove_result = await asyncio.to_thread(remove_tracker_instance, tracker_id)
            if not remove_result.get("success"):
                logger.warning(
                    "Failed to remove observation tracker instance %s: %s",
                    tracker_id,
                    remove_result,
                )
                return False

            state_name = get_tracking_state_name(tracker_id)
            async with AsyncSessionLocal() as dbsession:
                delete_reply = await trackingstate_crud.delete_tracking_state(dbsession, state_name)
            if not delete_reply.get("success"):
                logger.warning(
                    "Failed deleting tracking state '%s' for observation tracker %s: %s",
                    state_name,
                    tracker_id,
                    delete_reply,
                )
                return False

            await self._emit_tracker_instances_snapshot()
            return True
        except Exception as exc:
            logger.warning("Error removing observation tracker %s: %s", tracker_id, exc)
            return False

    @staticmethod
    def _resolve_tracker_id(rotator_config: Dict[str, Any]) -> str:
        owner_tracker_id = get_assigned_tracker_for_rotator(rotator_config.get("id"))
        if owner_tracker_id is None:
            return ""
        tracker_id = str(owner_tracker_id).strip()
        if not tracker_id or tracker_id.lower() == "none":
            return ""
        return tracker_id

    async def start_tracker_task(
        self,
        observation_id: str,
        satellite: Dict[str, Any],
        rotator_config: Dict[str, Any],
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Start rotator tracking for an observation.

        Args:
            observation_id: The observation ID
            satellite: Satellite information dict
            rotator_config: Rotator configuration dict
            tasks: List of observation tasks

        Returns:
            Dictionary with success/failure metadata
        """
        tracker_id = ""
        has_rotator = bool(rotator_config.get("id"))
        uses_observation_slot = False
        try:
            norad_id = satellite.get("norad_id")
            if not norad_id:
                return {
                    "success": False,
                    "error": "missing_target",
                    "message": "Observation has no target NORAD ID; tracker startup is mandatory.",
                }

            tracking_enabled = bool(rotator_config.get("tracking_enabled"))
            transmitter_id = self._extract_transmitter_id(tasks)
            rotator_id = rotator_config.get("id") if has_rotator else None
            satellite_name = str(satellite.get("name") or norad_id).strip() or str(norad_id)

            # Reuse existing target owner when available. Otherwise, use a dedicated
            # observation-scoped tracker slot that will be removed after the pass.
            if has_rotator:
                owner_tracker_id = get_assigned_tracker_for_rotator(rotator_id)
                if owner_tracker_id:
                    tracker_resolution = {
                        "success": True,
                        "tracker_id": owner_tracker_id,
                        "created": False,
                    }
                else:
                    tracker_resolution = create_observation_tracker_slot(observation_id)
                    uses_observation_slot = True
            else:
                tracker_resolution = create_observation_tracker_slot(observation_id)
                uses_observation_slot = True

            if not tracker_resolution.get("success"):
                return {
                    "success": False,
                    "error": tracker_resolution.get("error", "tracker_resolution_failed"),
                    "message": (
                        tracker_resolution.get("message") or "Failed to resolve tracker slot."
                    ),
                }
            tracker_id = str(tracker_resolution.get("tracker_id", "")).strip()
            if not tracker_id:
                return {
                    "success": False,
                    "error": "invalid_tracker_id",
                    "message": "Tracker resolution returned an invalid tracker ID.",
                }

            if has_rotator and uses_observation_slot:
                logger.info(
                    "Created observation tracker slot %s for rotator %s (observation %s)",
                    tracker_id,
                    rotator_id,
                    observation_id,
                )
            elif uses_observation_slot:
                logger.info(
                    "Created observation tracker slot %s for observation %s (no rotator)",
                    tracker_id,
                    observation_id,
                )

            tracker_manager = get_tracker_manager(tracker_id)

            requested_rotator_state = "disconnected"
            requested_rotator_id = rotator_id if has_rotator else "none"

            if has_rotator and tracking_enabled:
                requested_rotator_state = "tracking"
                unpark_before_tracking = bool(rotator_config.get("unpark_before_tracking", False))
                tracking_state = await tracker_manager.get_tracking_state() or {}
                current_rotator_state = str(tracking_state.get("rotator_state", "")).lower()

                # Optional unpark step before switching to tracking mode.
                if current_rotator_state == "parked" and unpark_before_tracking:
                    unpark_reply: Dict[str, Any] = await update_tracking_state_with_ownership(
                        tracker_id=tracker_id,
                        value={
                            "rotator_state": "connected",
                            "rotator_id": rotator_id,
                        },
                        requester_sid=f"observation:{observation_id}",
                    )
                    if not unpark_reply.get("success"):
                        return unpark_reply
                    await asyncio.sleep(0.2)

            tracking_reply: Dict[str, Any] = await update_tracking_state_with_ownership(
                tracker_id=tracker_id,
                value={
                    # Observation hijack must fully retarget tracker identity, not only NORAD.
                    # If command/body fields are left behind, the UI can keep rendering the
                    # previous mission/body identity for this slot.
                    "target_type": "satellite",
                    "target_name": satellite_name,
                    "norad_id": norad_id,
                    "group_id": satellite.get("group_id"),
                    "command": None,
                    "body_id": None,
                    "rotator_state": requested_rotator_state,
                    "rotator_id": requested_rotator_id,
                    "rig_state": "disconnected",  # Observations don't use rig for now
                    "rig_id": "none",
                    "transmitter_id": transmitter_id,
                    "rig_vfo": "none",
                    "vfo1": "uplink",
                    "vfo2": "downlink",
                },
                requester_sid=f"observation:{observation_id}",
            )
            if not tracking_reply.get("success"):
                if uses_observation_slot:
                    await self._remove_observation_tracker_instance(tracker_id)
                return tracking_reply

            await self._emit_tracker_instances_snapshot()

            logger.info(
                "Started tracker %s for observation %s: sat=%s (NORAD %s), mode=%s",
                tracker_id,
                observation_id,
                satellite.get("name"),
                norad_id,
                "tracking" if requested_rotator_state == "tracking" else "context-only",
            )
            return {
                "success": True,
                "tracker_id": tracker_id,
                "created": bool(tracker_resolution.get("created", False)),
                "reused_existing": not bool(tracker_resolution.get("created", False)),
                "ephemeral": uses_observation_slot,
            }

        except Exception as e:
            if tracker_id and uses_observation_slot:
                await self._remove_observation_tracker_instance(tracker_id)
            logger.error(f"Error starting tracker: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": "tracker_start_failed",
                "message": str(e),
            }

    async def stop_tracker_task(
        self,
        observation_id: str,
        rotator_config: Dict[str, Any],
        tracker_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Stop rotator tracking for an observation.

        Args:
            observation_id: The observation ID
            rotator_config: Rotator configuration dict
            tracker_context: Optional tracker metadata returned by start_tracker_task

        Returns:
            True if tracker stop/park operations succeeded
        """
        try:
            context = tracker_context or {}
            tracker_id = str(context.get("tracker_id") or "").strip()
            is_ephemeral = bool(context.get("ephemeral"))

            if is_ephemeral:
                if not tracker_id:
                    logger.warning(
                        "Observation %s has ephemeral tracker context without tracker_id",
                        observation_id,
                    )
                    return False
                removed = await self._remove_observation_tracker_instance(tracker_id)
                if removed:
                    logger.info(
                        "Removed ephemeral observation tracker %s for observation %s",
                        tracker_id,
                        observation_id,
                    )
                return removed

            if not rotator_config.get("tracking_enabled") or not rotator_config.get("id"):
                logger.debug(f"No rotator configured for observation {observation_id}")
                return True

            tracker_id = tracker_id or self._resolve_tracker_id(rotator_config)
            if not tracker_id:
                logger.debug(
                    "Skipping tracker stop for observation %s: no tracker currently assigned to rotator %s",
                    observation_id,
                    rotator_config.get("id"),
                )
                return True
            park_after_observation = bool(rotator_config.get("park_after_observation", False))

            if park_after_observation:
                park_reply = await update_tracking_state_with_ownership(
                    tracker_id=tracker_id,
                    value={
                        "rotator_state": "parked",
                        "rotator_id": rotator_config.get("id"),
                    },
                    requester_sid=f"observation:{observation_id}",
                )
                if not park_reply.get("success"):
                    logger.warning(
                        "Failed to park rotator for observation %s: %s",
                        observation_id,
                        park_reply,
                    )
                    return False
                logger.info(f"Parked rotator after observation {observation_id}")
            else:
                logger.debug(f"Leaving rotator connected after observation {observation_id}")

            return True
        except Exception as e:
            logger.error(f"Error stopping tracker for observation {observation_id}: {e}")
            logger.error(traceback.format_exc())
            return False
