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

"""Helper functions for observation executor."""

import traceback
from typing import Any, Optional

from common.logger import logger
from crud.scheduledobservations import log_observation_event, update_scheduled_observation_status
from db import AsyncSessionLocal
from observations.events import observation_sync


async def update_observation_status(
    sio: Any,
    observation_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    """
    Update observation status in database.

    Args:
        sio: Socket.IO server instance for event emission
        observation_id: The observation ID
        status: New status (RUNNING, COMPLETED, FAILED, CANCELLED)
        error_message: Optional error message for FAILED status
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await update_scheduled_observation_status(
                session, observation_id, status, error_message
            )
            if not result["success"]:
                logger.error(f"Failed to update observation status: {result.get('error')}")

        # Emit event to notify clients
        if sio:
            await sio.emit(
                "observation-status-update",
                {"id": observation_id, "status": status, "error": error_message},
            )

    except Exception as e:
        logger.error(f"Error updating observation status: {e}")
        logger.error(traceback.format_exc())


async def log_execution_event(observation_id: str, event: str, level: str = "info") -> None:
    """
    Log an execution event to the observation's execution_log.

    Args:
        observation_id: The observation ID
        event: Event description
        level: Event level (info, warning, error)
    """
    try:
        async with AsyncSessionLocal() as session:
            await log_observation_event(session, observation_id, event, level)
    except Exception as e:
        logger.error(f"Error logging execution event for {observation_id}: {e}")
        logger.error(traceback.format_exc())


async def remove_scheduled_stop_job(observation_id: str) -> None:
    """
    Remove the scheduled stop job for an observation.

    This is called when an observation fails to start or is aborted,
    to prevent the stop job from running in the future.

    Args:
        observation_id: The observation ID
    """
    try:
        if observation_sync:
            # Remove just the stop job
            job_id = f"obs_{observation_id}_stop"
            try:
                observation_sync.scheduler.remove_job(job_id)
                logger.info(f"Removed scheduled stop job for observation {observation_id}")
            except Exception as job_error:
                # Job might not exist, that's okay
                logger.debug(f"Stop job {job_id} not found or already removed: {job_error}")
    except Exception as e:
        logger.warning(f"Failed to remove scheduled stop job for {observation_id}: {e}")
