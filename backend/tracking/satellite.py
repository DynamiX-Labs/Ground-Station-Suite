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


import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from skyfield.api import EarthSatellite, load, wgs84


def get_satellite_az_el(
    home_lat: float,
    home_lon: float,
    satellite_tle_line1: str,
    satellite_tle_line2: str,
    observation_time: datetime,
) -> Tuple[float, float]:
    """
    Given a home location (latitude, longitude), a satellite TLE (two-line element),
    and a specific observation time, this function returns the
    azimuth and elevation of the satellite in degrees.

    Parameters:
    - home_lat: Latitude of the home location in degrees
    - home_lon: Longitude of the home location in degrees
    - satellite_tle_line1: First line of the satellite's TLE
    - satellite_tle_line2: Second line of the satellite's TLE
    - observation_time: A Python datetime representing the observation time (UTC)

    Returns:
    - (azimuth, elevation): Tuple (in degrees)
    """
    # Create a timescale and convert the observation time to a Skyfield time object
    ts = load.timescale()
    t = ts.from_datetime(observation_time)

    # Create the EarthSatellite object directly from the TLE strings
    satellite = EarthSatellite(satellite_tle_line1, satellite_tle_line2)

    # Define the observer's location
    observer = wgs84.latlon(home_lat, home_lon)

    # Compute the difference vector between a satellite and an observer
    difference = satellite - observer

    # Get the altitude (elevation) and azimuth in degrees
    alt, az, _ = difference.at(t).altaz()

    return round(az.degrees, 4), round(alt.degrees, 4)


def get_satellite_position_from_tle(tle_lines):
    """
    Computes the position and velocity of a satellite from its Two-Line Element (TLE) data.

    This function parses the provided TLE lines to create a satellite object and calculates
    its current geocentric position and velocity. It then determines the subpoint of the
    satellite (its latitude, longitude, and altitude above Earth's surface) and computes
    its velocity in kilometers per second.

    :param tle_lines: List of strings containing the TLE data for the satellite. The TLE must
        include exactly three lines: the satellite name, followed by two TLE lines.
    :type tle_lines: list[str]
    :return: A dictionary containing the latitude, longitude, altitude, and velocity of the satellite.
    :rtype: dict[str, float]
    """

    name = tle_lines[0].strip()
    line1 = tle_lines[1].strip()
    line2 = tle_lines[2].strip()

    # Load a timescale and get the current time.
    ts = load.timescale()
    t = ts.now()

    # Create an EarthSatellite object from the TLE.
    satellite = EarthSatellite(line1, line2, name, ts)

    # Compute the geocentric position for the current time.
    geocentric = satellite.at(t)

    # Obtain subpoint (latitude, longitude, and elevation above Earth).
    subpoint = geocentric.subpoint()

    lat_degrees = subpoint.latitude.degrees
    lon_degrees = subpoint.longitude.degrees
    altitude_m = subpoint.elevation.m  # altitude above Earth's surface in meters

    # Get velocity vector in km/s
    vx, vy, vz = geocentric.velocity.km_per_s
    velocity_km_s = math.sqrt(vx * vx + vy * vy + vz * vz)

    return {
        "lat": float(lat_degrees),
        "lon": float(lon_degrees),
        "alt": float(altitude_m),
        "vel": float(velocity_km_s),
    }


def get_satellite_path(
    tle: List[str], duration_minutes: float, step_minutes: float = 1.0
) -> Dict[str, List[List[Dict[str, float]]]]:
    """
    Computes the satellite's past and future path coordinates from its TLE.
    The path is computed at a fixed time step and then split into segments so that
    no segment contains a line crossing the dateline (+180 or -180 longitude).

    Args:
        tle: A list containing two TLE lines [line1, line2]
        duration_minutes: The projection duration (in minutes) for both past and future
        step_minutes: The time interval in minutes between coordinate samples

    Returns:
        An object with two properties:
        {
            'past': [[{lat, lon}], ...],
            'future': [[{lat, lon}], ...]
        }
        Each segment is a list of coordinate points that don't cross the dateline
    """

    try:
        # Load time scale
        ts = load.timescale()

        # Create satellite object from TLE
        if len(tle) != 2:
            raise ValueError("TLE must contain exactly two lines")

        satellite = EarthSatellite(tle[0], tle[1], "Satellite", ts)

        # Get current time
        now = datetime.now(timezone.utc)

        past_points = []
        future_points = []
        step_td = timedelta(minutes=step_minutes)

        # Compute past points: from (now - durationMinutes) up to now (inclusive)
        past_start = now - timedelta(minutes=duration_minutes)
        current = past_start

        while current <= now:
            time = ts.utc(
                current.year,
                current.month,
                current.day,
                current.hour,
                current.minute,
                current.second + current.microsecond / 1e6,
            )

            geocentric = satellite.at(time)
            subpoint = wgs84.subpoint(geocentric)

            lat = float(subpoint.latitude.degrees)
            lon = normalize_longitude(float(subpoint.longitude.degrees))

            past_points.append({"lat": lat, "lon": lon})
            current += step_td

        # Compute future points: from now up to (now + durationMinutes) (inclusive)
        future_end = now + timedelta(minutes=duration_minutes)
        current = now

        while current <= future_end:
            time = ts.utc(
                current.year,
                current.month,
                current.day,
                current.hour,
                current.minute,
                current.second + current.microsecond / 1e6,
            )

            geocentric = satellite.at(time)
            subpoint = wgs84.subpoint(geocentric)

            lat = float(subpoint.latitude.degrees)
            lon = normalize_longitude(float(subpoint.longitude.degrees))

            future_points.append({"lat": lat, "lon": lon})
            current += step_td

        # Split the past and future arrays into segments to avoid drawing lines across the dateline
        past_segments = split_at_dateline(past_points)
        future_segments = split_at_dateline(future_points)

        return {"past": past_segments, "future": future_segments}

    except Exception as e:
        print(f"Error computing satellite paths: {str(e)}")
        return {"past": [], "future": []}


def normalize_longitude(lon: float) -> float:
    """
    Normalize longitude to be in the range [-180, 180].

    Args:
        lon: The longitude value to normalize

    Returns:
        The normalized longitude value
    """
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


def split_at_dateline(points: List[Dict[str, float]]) -> List[List[Dict[str, float]]]:
    """
    Splits a list of coordinate points into segments so that no segment
    crosses the international date line (longitude ±180°).

    Args:
        points: A list of coordinate dictionaries with 'lat' and 'lon' keys

    Returns:
        A list of segments, where each segment is a list of coordinate points
    """
    if not points:
        return []

    segments = []
    current_segment = [points[0]]

    for i in range(1, len(points)):
        prev_point = points[i - 1]
        current_point = points[i]

        # Check if we cross the dateline (large longitude change)
        if abs(current_point["lon"] - prev_point["lon"]) > 180:
            # End the current segment
            segments.append(current_segment)
            # Start a new segment
            current_segment = [current_point]
        else:
            # Add point to the current segment
            current_segment.append(current_point)

    # Add the last segment if it's not empty
    if current_segment:
        segments.append(current_segment)

    return segments
