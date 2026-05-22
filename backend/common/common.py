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


import functools
import json
import math
import time
import uuid
from datetime import date, datetime, timedelta

import numpy
from skyfield.api import EarthSatellite, load, wgs84

from .logger import logger


class ModelEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        # Force allow_nan=False to raise errors instead of producing invalid JSON
        # We'll handle NaN/Infinity by converting to None in default()
        kwargs["allow_nan"] = False
        super().__init__(*args, **kwargs)

    def default(self, obj):

        if isinstance(obj, (date, datetime)):
            return obj.isoformat()

        if isinstance(obj, timedelta):
            return str(obj)

        if isinstance(obj, uuid.UUID):
            return str(obj)

        if isinstance(obj, bool):
            return bool(obj)

        # Handle numpy types
        if isinstance(obj, numpy.bool_):
            return bool(obj)

        if isinstance(obj, (numpy.integer, numpy.int_)):
            return int(obj)

        if isinstance(obj, (numpy.floating, numpy.float64)):
            value = float(obj)
            # Sanitize NaN and Infinity values to null for valid JSON
            # JavaScript's JSON.parse() cannot handle unquoted NaN/Infinity
            if not math.isfinite(value):
                return None
            return value

        # Attempt to convert SQLAlchemy model objects
        # by reading their columns
        try:
            return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
        except AttributeError:
            # If the object is not an SQLAlchemy model row, fallback
            return super().default(obj)

    def encode(self, o):
        # Sanitize the data structure before encoding to catch regular Python floats
        def sanitize(obj):
            if isinstance(obj, float):
                if not math.isfinite(obj):
                    return None
                return obj
            elif isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [sanitize(item) for item in obj]
            return obj

        sanitized = sanitize(o)
        return super().encode(sanitized)


def serialize_object(obj):
    """
    Serializes a Python object into a JSON-compatible format and then
    deserializes it back to a Python object. The serialization utilizes
    a custom JSON encoder, `ModelEncoder`, to handle potentially
    non-standard object types. The function ensures that the resulting
    object is JSON-compatible but has been reconstructed into its
    Python representation.

    :param obj: The Python object to be serialized and deserialized.
        This may include custom objects that require a specific
        JSON encoder, as well as built-in Python data structures.
    :return: The deserialized Python object resulting from the
        serialization and deserialization process. The output is a
        JSON-compatible Python object reconstructed to mimic the
        original input structure.
    """
    return json.loads(json.dumps(obj, cls=ModelEncoder))


def timeit(func):
    """Decorator that reports the execution time of the decorated function."""

    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        logger.info(f"Function '{func.__name__}' executed in {elapsed_time:.6f} seconds.")
        return result

    return wrapper


def async_timeit(func):
    """
    Async decorator that reports the execution time of the decorated coroutine.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        logger.info(f"Function '{func.__name__}' executed in {elapsed_time:.6f} seconds.")
        return result

    return wrapper


def is_geostationary(tle):
    """
    Determines whether a satellite is geostationary based on its TLE.

    :param tle: A list or tuple of two TLE lines [line1, line2].
    :return: True if the orbit is approximately geostationary, False otherwise.
    """
    if not isinstance(tle, (list, tuple)) or len(tle) < 2:
        raise ValueError("TLE must be a list or tuple containing two lines of valid TLE data.")

    line2 = tle[1]

    # According to the standard TLE format, the fields are at fixed character positions:
    # - Inclination (degrees):    columns 8-15
    # - RA of ascending node:     columns 17-24
    # - Eccentricity:            columns 26-32 (implied decimal point at the start)
    # - Argument of perigee:     columns 34-41
    # - Mean anomaly:            columns 43-50
    # - Mean motion (rev/day):   columns 52-62
    # - Revolution number:       columns 63-68

    # Extract inclination
    inclination_str = line2[8:16].strip()
    inclination_deg = float(inclination_str)

    # Extract eccentricity (the TLE format stores eccentricity as '0001234' => 0.0001234)
    eccentricity_str = line2[26:33].strip()
    eccentricity = float(f"0.{eccentricity_str}") if eccentricity_str else 0.0

    # Extract mean motion (revs per day)
    mean_motion_str = line2[52:63].strip()
    mean_motion = float(mean_motion_str)

    # Typical checks for geostationary orbit:
    # 1. Mean motion ~ 1 revolution per sidereal day (~1.0027 rev/day);
    #    we allow a small tolerance around 1.0 to 1.005 rev/day.
    # 2. Inclination near 0° (equatorial orbit)
    # 3. Eccentricity near 0 (circular orbit)

    # Define thresholds (these can be adjusted for stricter or looser checks)
    MEAN_MOTION_LOWER = 0.995  # Lower bound on mean motion
    MEAN_MOTION_UPPER = 1.005  # Upper bound on mean motion
    INCLINATION_MAX = 3.0  # Degrees
    ECCENTRICITY_MAX = 0.01  # Allowed eccentricity

    # Check each parameter
    is_mean_motion_ok = MEAN_MOTION_LOWER <= mean_motion <= MEAN_MOTION_UPPER
    is_inclination_ok = inclination_deg <= INCLINATION_MAX
    is_eccentricity_ok = eccentricity <= ECCENTRICITY_MAX

    return is_mean_motion_ok and is_inclination_ok and is_eccentricity_ok


def is_satellite_over_location(tle, date, target_lat, target_lon, threshold_km=500):
    """
    Determines if a satellite (from its TLE) is "over" a given lat/lon at a specified time.
    Uses Skyfield to compute the satellite subpoint and checks if that point is
    within `threshold_km` distance of the target location.

    :param tle: A list or tuple of two strings: [line1, line2] containing the satellite's TLE.
    :param date: A Python datetime (UTC) for when to check.
    :param target_lat: Target latitude in degrees (negative for south).
    :param target_lon: Target longitude in degrees (negative for west).
    :param threshold_km: Distance threshold in kilometers. If the satellite’s subpoint
                         is within this distance, we consider it "over" the location.
    :return: True if the satellite is within threshold_km of the target location; False otherwise.
    """
    if not isinstance(tle, (list, tuple)) or len(tle) < 2:
        raise ValueError("TLE must be a list or tuple with two lines of data.")

    line1, line2 = tle

    # create a Skyfield Timescale and convert Python datetime to a Skyfield Time object
    ts = load.timescale()
    # If `date` is a naive datetime, treat it as UTC. If it's timezone-aware, .utc_datetime() might be needed.
    t = ts.from_datetime(date)

    # construct the EarthSatellite object from the TLE lines
    satellite = EarthSatellite(line1, line2, name="Sat", ts=ts)

    # compute the satellite's position at the given time
    difference = satellite.at(t)

    # compute the subpoint (geodetic point directly below the satellite)
    subpoint = difference.subpoint()
    sat_lat = subpoint.latitude.degrees
    sat_lon = subpoint.longitude.degrees

    # use Skyfield's built-in geometry to compute distance to the target location
    target_location = wgs84.latlon(target_lat, target_lon)
    sat_position = wgs84.latlon(sat_lat, sat_lon)
    distance_km = target_location.distance_to(sat_position).km

    # check if the satellite’s subpoint is within `threshold_km` of target lat/lon
    return distance_km <= threshold_km
