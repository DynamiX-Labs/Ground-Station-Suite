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

"""Tracker message handling for Socket.IO events."""

import asyncio
import logging
from typing import Any, Dict

from common.constants import SocketEvents
from tracker.contracts import InvalidTrackerIdError, require_tracker_id
from tracker.runner import get_existing_tracker_manager, queue_from_tracker
from vfos.updates import handle_vfo_updates_for_tracking

logger = logging.getLogger(__name__)

# Global storage for tracker stats (accessed by performance monitor)
tracker_stats: Dict[str, Any] = {}


async def handle_tracker_messages(sockio):
    """
    Continuously checks for messages from the tracker process.

    Processes messages from the tracker queue and emits them as Socket.IO events.
    Also handles VFO updates for SDR tracking when satellite-tracking events are received.

    Args:
        sockio: Socket.IO server instance for emitting events
    """
    while True:
        try:
            if queue_from_tracker is not None and not queue_from_tracker.empty():
                message = queue_from_tracker.get_nowait()
                msg_type = message.get("type")
                event = message.get("event")
                data = message.get("data", {})
                if not isinstance(data, dict):
                    data = {}

                # Handle stats messages
                if msg_type == "stats":
                    global tracker_stats
                    try:
                        tracker_id = require_tracker_id(message.get("tracker_id"))
                    except InvalidTrackerIdError:
                        logger.debug("Dropping stats message without tracker_id")
                        await asyncio.sleep(0)
                        continue
                    tracker_stats[tracker_id] = message.get("stats", {})
                elif event:
                    try:
                        tracker_id = require_tracker_id(
                            message.get("tracker_id") or data.get("tracker_id")
                        )
                    except InvalidTrackerIdError:
                        logger.debug("Dropping tracker event '%s' without tracker_id", event)
                        await asyncio.sleep(0)
                        continue
                    data["tracker_id"] = tracker_id
                    await sockio.emit(event, data)
                    if event == SocketEvents.SATELLITE_TRACKING:
                        await sockio.emit(SocketEvents.SATELLITE_TRACKING_V2, data)

                    # Handle VFO updates for SDR tracking
                    if event == "satellite-tracking" and data.get("rig_data"):
                        await handle_vfo_updates_for_tracking(sockio, data)
                    if event == SocketEvents.SATELLITE_TRACKING:
                        try:
                            manager = get_existing_tracker_manager(tracker_id)
                            if manager is None:
                                await asyncio.sleep(0)
                                continue
                            status_events = manager.process_tracking_update(data)
                            for status in status_events:
                                await sockio.emit(SocketEvents.TRACKER_COMMAND_STATUS, status)
                        except RuntimeError:
                            logger.debug(
                                "TrackerManager not initialized while processing tracking update"
                            )

            await asyncio.sleep(0.1)
        except Exception as e:  # pragma: no cover - best effort
            logger.error(f"Error handling tracker messages: {e}")
            await asyncio.sleep(1)
