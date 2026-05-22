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

import re
import traceback
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.common import logger, serialize_object
from db.models import MonitoredSatellites, ScheduledObservations

# Compiled regex patterns for parsing integrity errors
UNIQUE_CONSTRAINT_PATTERN = re.compile(r"UNIQUE constraint failed: \w+\.(\w+)")
FOREIGN_KEY_PATTERN = re.compile(r"FOREIGN KEY constraint failed")


def _transform_to_db_format(data: dict) -> dict:
    """Transform handler format to database format."""
    # Extract hardware IDs and convert to UUID
    sessions = data.get("sessions", []) or []
    primary_session = sessions[0] if sessions else {}
    sdr_id = primary_session.get("sdr", {}).get("id") if isinstance(primary_session, dict) else None
    if sdr_id and isinstance(sdr_id, str):
        sdr_id = uuid.UUID(sdr_id)

    rotator_id = data.get("rotator", {}).get("id") if data.get("rotator") else None
    if rotator_id and isinstance(rotator_id, str):
        rotator_id = uuid.UUID(rotator_id)

    rig_id = data.get("rig", {}).get("id") if data.get("rig") else None
    if rig_id and isinstance(rig_id, str):
        rig_id = uuid.UUID(rig_id)

    # Extract satellite info
    satellite = data.get("satellite", {})
    norad_id = satellite.get("norad_id")

    # Build grouped JSON configs
    satellite_config = {
        "name": satellite.get("name"),
        "group_id": satellite.get("group_id"),
    }

    rotator_config = dict(data.get("rotator", {}) or {})
    rotator_config.pop("tracker_id", None)

    hardware_config = {
        "rotator": rotator_config,
        "rig": data.get("rig", {}),
    }

    generation_config = {
        "min_elevation": data.get("min_elevation", 20),
        "task_start_elevation": data.get("task_start_elevation", 10),
        "lookahead_hours": data.get("lookahead_hours", 24),
    }

    return {
        "id": data.get("id"),
        "enabled": data.get("enabled", True),
        "norad_id": norad_id,
        "sdr_id": sdr_id,
        "rotator_id": rotator_id,
        "rig_id": rig_id,
        "satellite_config": satellite_config,
        "hardware_config": hardware_config,
        "generation_config": generation_config,
        "sessions": sessions,
        "created_at": (
            datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            if "created_at" in data
            else datetime.now(timezone.utc)
        ),
        "updated_at": (
            datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            if "updated_at" in data
            else datetime.now(timezone.utc)
        ),
    }


def _transform_from_db_format(db_obj: dict) -> dict:
    """Transform database format back to handler format."""
    hardware_config = db_obj.get("hardware_config", {})
    satellite_config = db_obj.get("satellite_config", {})
    generation_config = db_obj.get("generation_config", {})
    sessions = db_obj.get("sessions", []) or []

    # Handle datetime fields - they may already be strings after serialize_object
    created_at = db_obj.get("created_at")
    if created_at and hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    updated_at = db_obj.get("updated_at")
    if updated_at and hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()

    rotator_config = dict(hardware_config.get("rotator", {}) or {})
    rotator_config.pop("tracker_id", None)

    return {
        "id": db_obj.get("id"),
        "enabled": db_obj.get("enabled"),
        "satellite": {
            "norad_id": db_obj.get("norad_id"),
            "name": satellite_config.get("name"),
            "group_id": satellite_config.get("group_id"),
        },
        "rotator": rotator_config,
        "rig": hardware_config.get("rig", {}),
        "min_elevation": generation_config.get("min_elevation", 20),
        "task_start_elevation": generation_config.get("task_start_elevation", 10),
        "lookahead_hours": generation_config.get("lookahead_hours", 24),
        "sessions": sessions,
        "created_at": created_at,
        "updated_at": updated_at,
    }


async def fetch_monitored_satellites(
    session: AsyncSession, satellite_id: Optional[str] = None
) -> dict:
    """
    Fetch a single monitored satellite by ID or all if ID is not provided.
    """
    try:
        if satellite_id is not None:
            stmt = select(MonitoredSatellites).filter(MonitoredSatellites.id == satellite_id)
            result = await session.execute(stmt)
            satellite = result.scalar_one_or_none()
            if satellite:
                satellite = serialize_object(satellite)
                satellite = _transform_from_db_format(satellite)
        else:
            stmt = select(MonitoredSatellites).order_by(MonitoredSatellites.created_at)
            result = await session.execute(stmt)
            satellites = result.scalars().all()
            satellite = [_transform_from_db_format(serialize_object(sat)) for sat in satellites]

        return {"success": True, "data": satellite, "error": None}

    except Exception as e:
        logger.error(f"Error fetching monitored satellites: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def fetch_monitored_satellite_by_norad(session: AsyncSession, norad_id: int) -> dict:
    """
    Fetch a monitored satellite by NORAD ID.
    """
    try:
        stmt = select(MonitoredSatellites).filter(MonitoredSatellites.norad_id == norad_id)
        result = await session.execute(stmt)
        satellite = result.scalar_one_or_none()

        if satellite:
            satellite = serialize_object(satellite)
            satellite = _transform_from_db_format(satellite)

        return {"success": True, "data": satellite, "error": None}

    except Exception as e:
        logger.error(f"Error fetching monitored satellite by NORAD ID: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def fetch_enabled_monitored_satellites(session: AsyncSession) -> dict:
    """
    Fetch all enabled monitored satellites.
    """
    try:
        stmt = (
            select(MonitoredSatellites)
            .filter(MonitoredSatellites.enabled.is_(True))
            .order_by(MonitoredSatellites.created_at)
        )
        result = await session.execute(stmt)
        satellites = result.scalars().all()
        satellites = [_transform_from_db_format(serialize_object(sat)) for sat in satellites]

        return {"success": True, "data": satellites, "error": None}

    except Exception as e:
        logger.error(f"Error fetching enabled monitored satellites: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def add_monitored_satellite(session: AsyncSession, data: dict) -> dict:
    """
    Create and add a new monitored satellite record.
    """
    try:
        db_data = _transform_to_db_format(data)

        stmt = insert(MonitoredSatellites).values(**db_data).returning(MonitoredSatellites)
        result = await session.execute(stmt)
        await session.commit()

        new_satellite = result.scalar_one()
        new_satellite = serialize_object(new_satellite)
        new_satellite = _transform_from_db_format(new_satellite)

        return {"success": True, "data": new_satellite, "error": None}

    except IntegrityError as e:
        await session.rollback()
        logger.warning(f"Database integrity error adding monitored satellite: {e}")

        # Extract the original database error message
        error_str = str(e.orig) if hasattr(e, "orig") else str(e)

        # Check for UNIQUE constraint violations
        match = UNIQUE_CONSTRAINT_PATTERN.search(error_str)
        if match:
            field = match.group(1)
            # Provide specific message for norad_id (the only unique field in this table)
            if field == "norad_id":
                norad_id = data.get("satellite", {}).get("norad_id")
                sat_name = data.get("satellite", {}).get("name", "Unknown")
                return {
                    "success": False,
                    "error": f"Satellite {sat_name} (NORAD ID: {norad_id}) is already being monitored.",
                }
            return {"success": False, "error": f"A record with this {field} already exists."}

        # Check for FOREIGN KEY constraint violations
        if FOREIGN_KEY_PATTERN.search(error_str):
            return {
                "success": False,
                "error": "Invalid reference: One or more selected items (SDR, Rotator, or Rig) no longer exist.",
            }

        # Generic integrity error fallback
        return {"success": False, "error": f"Database constraint violation: {error_str}"}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding monitored satellite: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def edit_monitored_satellite(session: AsyncSession, data: dict) -> dict:
    """
    Edit an existing monitored satellite record.
    """
    try:
        satellite_id = data.get("id")
        if not satellite_id:
            return {"success": False, "error": "Monitored satellite ID is required"}

        db_data = _transform_to_db_format(data)
        # Remove id from update data
        db_data.pop("id", None)
        # Always update the timestamp
        db_data["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(MonitoredSatellites)
            .where(MonitoredSatellites.id == satellite_id)
            .values(**db_data)
            .returning(MonitoredSatellites)
        )
        result = await session.execute(stmt)
        await session.commit()

        updated_satellite = result.scalar_one_or_none()
        if not updated_satellite:
            return {"success": False, "error": f"Monitored satellite not found: {satellite_id}"}

        updated_satellite = serialize_object(updated_satellite)
        updated_satellite = _transform_from_db_format(updated_satellite)

        return {"success": True, "data": updated_satellite, "error": None}

    except IntegrityError as e:
        await session.rollback()
        logger.warning(f"Database integrity error editing monitored satellite: {e}")

        # Extract the original database error message
        error_str = str(e.orig) if hasattr(e, "orig") else str(e)

        # Check for UNIQUE constraint violations
        match = UNIQUE_CONSTRAINT_PATTERN.search(error_str)
        if match:
            field = match.group(1)
            # Provide specific message for norad_id (the only unique field in this table)
            if field == "norad_id":
                norad_id = data.get("satellite", {}).get("norad_id")
                sat_name = data.get("satellite", {}).get("name", "Unknown")
                return {
                    "success": False,
                    "error": f"Satellite {sat_name} (NORAD ID: {norad_id}) is already being monitored.",
                }
            return {"success": False, "error": f"A record with this {field} already exists."}

        # Check for FOREIGN KEY constraint violations
        if FOREIGN_KEY_PATTERN.search(error_str):
            return {
                "success": False,
                "error": "Invalid reference: One or more selected items (SDR, Rotator, or Rig) no longer exist.",
            }

        # Generic integrity error fallback
        return {"success": False, "error": f"Database constraint violation: {error_str}"}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error editing monitored satellite: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def toggle_monitored_satellite_enabled(
    session: AsyncSession, satellite_id: str, enabled: bool
) -> dict:
    """
    Toggle the enabled status of a monitored satellite.
    Only updates the enabled field without modifying other fields.
    """
    try:
        stmt = (
            update(MonitoredSatellites)
            .where(MonitoredSatellites.id == satellite_id)
            .values(enabled=enabled, updated_at=datetime.now(timezone.utc))
            .returning(MonitoredSatellites)
        )
        result = await session.execute(stmt)
        await session.commit()

        updated_satellite = result.scalar_one_or_none()
        if not updated_satellite:
            return {"success": False, "error": f"Monitored satellite not found: {satellite_id}"}

        return {"success": True, "data": {"id": satellite_id, "enabled": enabled}}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error toggling monitored satellite enabled status: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def delete_monitored_satellites(
    session: AsyncSession, ids: List[str], delete_observations: bool = False
) -> dict:
    """
    Delete one or more monitored satellite records.

    Args:
        session: Database session
        ids: List of monitored satellite IDs to delete
        delete_observations: If True, also delete all scheduled observations
                           associated with these monitored satellites

    Returns:
        Dictionary with success status and deletion counts
    """
    try:
        deleted_observations_count = 0

        # First, delete associated observations if requested
        if delete_observations:
            obs_stmt = delete(ScheduledObservations).where(
                ScheduledObservations.monitored_satellite_id.in_(ids)
            )
            obs_result = await session.execute(obs_stmt)
            deleted_observations_count = obs_result.rowcount
            logger.info(
                f"Deleted {deleted_observations_count} scheduled observations "
                f"associated with monitored satellites: {ids}"
            )

        # Then delete the monitored satellites
        stmt = delete(MonitoredSatellites).where(MonitoredSatellites.id.in_(ids))
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount
        return {
            "success": True,
            "data": {
                "deleted": deleted_count,
                "deleted_observations": deleted_observations_count,
            },
            "error": None,
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting monitored satellites: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


# ============================================================================
# AUTO-GENERATED OBSERVATIONS HELPERS
# ============================================================================


async def mark_observation_as_generated(
    session: AsyncSession, observation_id: str, monitored_satellite_id: str
) -> dict:
    """
    Mark an observation as auto-generated from a monitored satellite.
    Updates the observation's monitored_satellite_id and generated_at fields.
    """
    try:
        stmt = (
            update(ScheduledObservations)
            .where(ScheduledObservations.id == observation_id)
            .values(
                monitored_satellite_id=monitored_satellite_id,
                generated_at=datetime.now(timezone.utc),
            )
        )
        await session.execute(stmt)
        await session.commit()

        return {"success": True, "data": None, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error marking observation as generated: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def fetch_generated_observations_for_satellite(
    session: AsyncSession, monitored_satellite_id: str
) -> dict:
    """
    Fetch all observation IDs generated by a monitored satellite.
    """
    try:
        stmt = select(ScheduledObservations.id).filter(
            ScheduledObservations.monitored_satellite_id == monitored_satellite_id
        )
        result = await session.execute(stmt)
        observation_ids = [row[0] for row in result.all()]

        return {"success": True, "data": observation_ids, "error": None}

    except Exception as e:
        logger.error(f"Error fetching generated observations: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def delete_generated_observations_for_satellite(
    session: AsyncSession, monitored_satellite_id: str
) -> dict:
    """
    Delete all observations that were auto-generated from a monitored satellite.
    """
    try:
        stmt = delete(ScheduledObservations).where(
            ScheduledObservations.monitored_satellite_id == monitored_satellite_id
        )
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount
        return {"success": True, "data": {"deleted": deleted_count}, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting generated observations: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}
