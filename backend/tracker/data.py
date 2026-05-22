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


import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, TypedDict, Union

import crud
from common.common import is_geostationary, serialize_object
from db import AsyncSessionLocal
from orbits import CentralBody, get_propagation_input
from tracker.contracts import get_tracking_state_name
from tracking.footprint import get_satellite_coverage_circle
from tracking.satellite import (
    get_satellite_az_el,
    get_satellite_path,
    get_satellite_position_from_tle,
)


class SatelliteDetails(TypedDict):
    """Type definition for satellite details."""

    name: str
    tle1: str
    tle2: str
    norad_id: int
    is_geostationary: bool


class SatellitePosition(TypedDict):
    """Type definition for satellite position."""

    lat: float
    lon: float
    alt: float
    az: float
    el: float


class SatellitePaths(TypedDict):
    """Type definition for satellite paths."""

    past: List[Any]
    future: List[Any]


class SatelliteData(TypedDict):
    """Type definition for compiled satellite data."""

    details: SatelliteDetails
    position: SatellitePosition
    paths: SatellitePaths
    coverage: List[Any]
    transmitters: List[Any]
    error: bool


logger = logging.getLogger("tracker-worker")


class CacheManager:
    """
    A generic caching system that stores computed values with expiration times.
    Designed to be extensible for different types of cached data.
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a unique cache key based on prefix and parameters."""
        # Sort kwargs to ensure consistent key generation
        sorted_params = sorted(kwargs.items())
        param_string = "_".join([f"{k}={v}" for k, v in sorted_params])

        # Create hash of parameters to handle long parameter strings
        param_hash = hashlib.md5(param_string.encode()).hexdigest()
        return f"{prefix}_{param_hash}"

    def get(self, cache_key: str) -> Optional[Any]:
        """Retrieve cached value if it exists and hasn't expired."""
        if cache_key not in self._cache:
            return None

        cache_entry = self._cache[cache_key]

        # Check if cache has expired
        if datetime.now(timezone.utc) > cache_entry["expires_at"]:
            del self._cache[cache_key]
            return None

        logger.debug(f"Cache hit for key: {cache_key}")
        return cache_entry["data"]

    def set(self, cache_key: str, data: Any, ttl_minutes: int = 30) -> None:
        """Store data in cache with specified time-to-live."""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        self._cache[cache_key] = {
            "data": data,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        }

        logger.debug(f"Cached data with key: {cache_key}, expires at: {expires_at}")

    def clear_expired(self) -> int:
        """Remove all expired cache entries and return count of removed items."""
        now = datetime.now(timezone.utc)
        expired_keys = [key for key, entry in self._cache.items() if now > entry["expires_at"]]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        now = datetime.now(timezone.utc)
        expired_count = sum(1 for entry in self._cache.values() if now > entry["expires_at"])

        return {
            "total_entries": len(self._cache),
            "expired_entries": expired_count,
            "active_entries": len(self._cache) - expired_count,
        }


# Global cache manager instance
cache_manager = CacheManager()


def get_cached_satellite_paths(
    tle1: str, tle2: str, duration_minutes: int, step_minutes: float
) -> Optional[dict]:
    """
    Retrieve cached satellite paths if available and not expired.

    :param tle1: First line of TLE data
    :param tle2: Second line of TLE data
    :param duration_minutes: Duration for path calculation
    :param step_minutes: Step size in minutes
    :return: Cached paths or None if not available
    """
    cache_key = cache_manager._generate_cache_key(
        "satellite_paths", tle1=tle1, tle2=tle2, duration=duration_minutes, step=step_minutes
    )

    return cache_manager.get(cache_key)


def cache_satellite_paths(
    tle1: str,
    tle2: str,
    duration_minutes: int,
    step_minutes: float,
    paths: dict,
    ttl_minutes: int = 30,
) -> None:
    """
    Cache satellite paths with specified TTL.

    :param tle1: First line of TLE data
    :param tle2: Second line of TLE data
    :param duration_minutes: Duration for path calculation
    :param step_minutes: Step size in minutes
    :param paths: Path data to cache
    :param ttl_minutes: Time to live in minutes (default: 30)
    """
    cache_key = cache_manager._generate_cache_key(
        "satellite_paths", tle1=tle1, tle2=tle2, duration=duration_minutes, step=step_minutes
    )

    cache_manager.set(cache_key, paths, ttl_minutes)


async def compiled_satellite_data(dbsession, norad_id: int) -> Dict[str, Any]:
    """
    Compiles detailed information about a satellite, including its orbital details,
    transmitters, and sky position based on tracking data and user's location.
    Now uses caching for expensive path calculations.

    :param dbsession: Database session object used to interact with the database
    :param norad_id: Tracking state dictionary containing satellite tracking data
    :return: Dictionary containing satellite details, transmitters, and position
    :rtype: dict
    :raises Exception: If satellite tracking data is unavailable or incomplete
    :raises Exception: If no satellite matches the provided NORAD ID
    :raises Exception: If more than one satellite is found for the same NORAD ID
    :raises Exception: If user location is not found in the database
    """

    satellite_data: Dict[str, Any] = {
        "details": {},
        "position": {},
        "paths": {"past": [], "future": []},
        "coverage": [],
        "transmitters": [],
        "error": False,
    }

    try:

        satellite = await crud.satellites.fetch_satellites(dbsession, norad_id=norad_id)

        if not satellite.get("success", False):
            raise Exception(f"No satellite found in the db for norad id {norad_id}")

        if len(satellite.get("data", [])) != 1:
            raise Exception(
                f"Expected exactly one satellite in the result for norad id {norad_id} got"
                f" {len(satellite.get('data', []))}"
            )

        satellite_details: Dict[str, Any] = satellite["data"][0]
        propagation_input = get_propagation_input(satellite_details, central_body=CentralBody.EARTH)
        satellite_data["details"] = dict(satellite_details)
        satellite_data["details"]["tle1"] = propagation_input.tle1
        satellite_data["details"]["tle2"] = propagation_input.tle2
        satellite_data["details"]["is_geostationary"] = is_geostationary(
            [propagation_input.tle1, propagation_input.tle2]
        )

        # get target map settings
        target_map_settings_reply = await crud.preferences.get_map_settings(
            dbsession, "target-map-settings"
        )
        target_map_settings = target_map_settings_reply["data"].get("value", {})

        # fetch transmitters
        transmitters = await crud.transmitters.fetch_transmitters_for_satellite(
            dbsession, norad_id=norad_id
        )
        satellite_data["transmitters"] = transmitters["data"]

        location = await crud.locations.fetch_all_locations(dbsession)
        if (
            not location.get("success", False)
            or not location.get("data")
            or len(location["data"]) == 0
        ):
            raise Exception("No location found in the db, please set one")

        # Use the first location from the list
        location_data: Dict[str, Any] = location["data"][0]

        # get current position
        position = get_satellite_position_from_tle(
            [
                satellite_details["name"],
                propagation_input.tle1,
                propagation_input.tle2,
            ]
        )

        # get position in the sky
        home_lat = location_data["lat"]
        home_lon = location_data["lon"]
        sky_point = get_satellite_az_el(
            home_lat,
            home_lon,
            propagation_input.tle1,
            propagation_input.tle2,
            datetime.now(timezone.utc),
        )

        # calculate paths with caching
        tle1 = propagation_input.tle1
        tle2 = propagation_input.tle2
        duration_minutes = int(target_map_settings.get("orbitProjectionDuration", 240))
        step_minutes = 0.5

        # Try to get cached paths first
        cached_paths = get_cached_satellite_paths(tle1, tle2, duration_minutes, step_minutes)

        # Check for cached items
        if cached_paths is not None:
            logger.debug(f"Using cached satellite paths for NORAD ID: {norad_id}")
            satellite_data["paths"] = cached_paths
        else:
            logger.info(f"Computing new satellite paths for NORAD ID: {norad_id}")
            paths = get_satellite_path(
                [tle1, tle2], duration_minutes=duration_minutes, step_minutes=step_minutes
            )

            # Cache the computed paths for 30 minutes
            cache_satellite_paths(tle1, tle2, duration_minutes, step_minutes, paths, ttl_minutes=30)
            satellite_data["paths"] = paths

        # Add the coverage (footprint)
        satellite_data["coverage"] = get_satellite_coverage_circle(
            position["lat"], position["lon"], position["alt"] / 1000, num_points=300
        )

        position["az"] = sky_point[0]
        position["el"] = sky_point[1]
        satellite_data["position"] = position

        satellite_data = serialize_object(satellite_data)

    except Exception as e:
        logger.error(f"Failed to compile satellite data for norad id: {norad_id}, error: {e}")
        logger.exception(e)
        satellite_data["error"] = True

    return satellite_data


def compiled_satellite_data_from_inputs(
    satellite: Dict[str, Any],
    location: Dict[str, Any],
    transmitters: Optional[List[Any]] = None,
    map_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compile satellite data using in-memory inputs instead of database access.
    """
    satellite_data: Dict[str, Any] = {
        "details": {},
        "position": {},
        "paths": {"past": [], "future": []},
        "coverage": [],
        "transmitters": transmitters or [],
        "error": False,
    }

    try:
        if not satellite or not location:
            raise Exception("Missing satellite or location data")

        propagation_input = get_propagation_input(satellite, central_body=CentralBody.EARTH)
        satellite_details = {
            "name": satellite.get("name"),
            "tle1": propagation_input.tle1,
            "tle2": propagation_input.tle2,
            "norad_id": satellite.get("norad_id"),
        }
        satellite_details["is_geostationary"] = is_geostationary(
            [propagation_input.tle1, propagation_input.tle2]
        )
        satellite_data["details"] = satellite_details

        # get current position
        position = get_satellite_position_from_tle(
            [
                satellite_details["name"],
                propagation_input.tle1,
                propagation_input.tle2,
            ]
        )

        home_lat = location["lat"]
        home_lon = location["lon"]
        sky_point = get_satellite_az_el(
            home_lat,
            home_lon,
            propagation_input.tle1,
            propagation_input.tle2,
            datetime.now(timezone.utc),
        )

        # calculate paths with caching
        duration_minutes = int((map_settings or {}).get("orbitProjectionDuration", 240))
        step_minutes = 0.5

        tle1 = propagation_input.tle1
        tle2 = propagation_input.tle2

        cached_paths = get_cached_satellite_paths(
            tle1,
            tle2,
            duration_minutes,
            step_minutes,
        )
        if cached_paths is not None:
            satellite_data["paths"] = cached_paths
        else:
            paths = get_satellite_path(
                [tle1, tle2],
                duration_minutes=duration_minutes,
                step_minutes=step_minutes,
            )
            cache_satellite_paths(
                tle1,
                tle2,
                duration_minutes,
                step_minutes,
                paths,
                ttl_minutes=30,
            )
            satellite_data["paths"] = paths

        satellite_data["coverage"] = get_satellite_coverage_circle(
            position["lat"], position["lon"], position["alt"] / 1000, num_points=300
        )

        position["az"] = sky_point[0]
        position["el"] = sky_point[1]
        satellite_data["position"] = position
        satellite_data = serialize_object(satellite_data)

    except Exception as e:
        logger.error(f"Failed to compile satellite data from inputs, error: {e}")
        logger.exception(e)
        satellite_data["error"] = True

    return satellite_data


async def get_ui_tracker_state(group_id: str, norad_id: int, tracker_id: str):
    """
    Fetches the current tracker state for a specified group ID and satellite ID. This function
    interacts with the tracking database using asynchronous functions to retrieve data related
    to the specified identifiers. The response contains the success status and fetched data,
    or an error on failure.

    :param group_id: The unique identifier for the group whose satellites are to be fetched.
    :type group_id: int
    :param norad_id: The unique identifier for the satellite whose state is to be fetched.
    :type norad_id: int
    :return: A dictionary containing the success status and the tracker state data, or None
        if the operation fails.
    :rtype: dict
    """
    reply: Dict[str, Union[bool, None, Dict[str, Any]]] = {"success": False, "data": None}

    data: Dict[str, Any] = {
        "groups": [],
        "satellites": [],
        "transmitters": [],
        "group_id": None,
        "norad_id": None,
        "rotator_id": "none",
        "rig_id": "none",
        "transmitter_id": "none",
    }

    try:
        async with AsyncSessionLocal() as dbsession:
            groups = await crud.groups.fetch_satellite_group(dbsession)

            # Only fetch satellites when group_id is a valid UUID.
            group_id_is_valid_uuid = False
            if group_id and group_id != "":
                try:
                    uuid.UUID(str(group_id))
                    group_id_is_valid_uuid = True
                except (ValueError, TypeError):
                    group_id_is_valid_uuid = False

            if group_id_is_valid_uuid:
                satellites = await crud.satellites.fetch_satellites_for_group_id(
                    dbsession, group_id=group_id
                )
            else:
                satellites = {"success": True, "data": []}

            tracking_state_name = get_tracking_state_name(tracker_id)
            tracking_state = await crud.trackingstate.get_tracking_state(
                dbsession, name=tracking_state_name
            )
            transmitters = await crud.transmitters.fetch_transmitters_for_satellite(
                dbsession, norad_id=norad_id
            )
            data["groups"] = groups["data"]
            data["satellites"] = satellites["data"]
            data["group_id"] = group_id
            data["norad_id"] = norad_id
            tracking_value = (tracking_state.get("data") or {}).get("value", {}) or {}
            data["rig_id"] = tracking_value.get("rig_id", "none")
            data["rotator_id"] = tracking_value.get("rotator_id", "none")
            data["transmitter_id"] = tracking_value.get("transmitter_id", "none")
            data["transmitters"] = transmitters["data"]
            reply["success"] = True
            reply["data"] = data

    except Exception as e:
        logger.error(
            f"Failed to get tracker state for group id: {group_id}, satellite id: {norad_id}, error: {e}"
        )
        logger.exception(e)

    finally:
        pass

    return reply


# Utility functions for cache management
async def clear_expired_cache():
    """Clear expired cache entries. Can be called periodically."""
    cleared_count = cache_manager.clear_expired()
    if cleared_count > 0:
        logger.info(f"Cleared {cleared_count} expired cache entries")
    return cleared_count


async def get_cache_statistics():
    """Get current cache statistics."""
    return cache_manager.get_cache_stats()
