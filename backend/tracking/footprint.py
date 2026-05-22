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


def get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km, num_points=36):
    """
    Returns an array of { "lat": lat, "lon": lon } points representing the satellite's
    coverage area on Earth (its horizon circle), adjusted so that if the area
    includes the north or South Pole, a vertex for that pole is inserted.

    Args:
        sat_lat (float): Satellite latitude in degrees.
        sat_lon (float): Satellite longitude in degrees.
        altitude_km (float): Satellite altitude above Earth's surface in km.
        num_points (int, optional): Number of segments for the circle boundary.
                                  (The resulting array will have num_points+1 points.)

    Returns:
        list: The polygon (in degrees) for the coverage area, as a list of dicts with lat/lon keys.
    """
    # Mean Earth radius in kilometers (WGS-84 approximate)
    R_EARTH = 6378.137

    # Validate altitude to prevent math domain errors
    if altitude_km <= -R_EARTH:
        # Handle invalid altitude (satellite below Earth's center)
        return [{"lat": sat_lat, "lon": sat_lon}]  # Return just the subpoint

    # Convert satellite subpoint to radians
    lat0 = (sat_lat * math.pi) / 180
    lon0 = (sat_lon * math.pi) / 180

    # Compute the angular radius of the coverage circle (in radians)
    # Ensure the argument to acos stays within [-1, 1]
    arg = R_EARTH / (R_EARTH + altitude_km)
    arg = max(-1.0, min(1.0, arg))  # Clamp value to valid range
    d = math.acos(arg)

    # Check if coverage includes the North or South Pole
    north_pole_included = lat0 + d > math.pi / 2
    south_pole_included = lat0 - d < -math.pi / 2

    # Generate the circle points (closed polygon)
    circle_points = []

    # Add the regular circle points
    for i in range(num_points + 1):
        theta = (2 * math.pi * i) / num_points

        # Using spherical trigonometry to compute a point d away from (lat0,lon0)
        lat_i = math.asin(
            math.sin(lat0) * math.cos(d) + math.cos(lat0) * math.sin(d) * math.cos(theta)
        )
        lon_i = lon0 + math.atan2(
            math.sin(d) * math.sin(theta) * math.cos(lat0),
            math.cos(d) - math.sin(lat0) * math.sin(lat_i),
        )

        # Convert back to degrees
        lat_deg = (lat_i * 180) / math.pi
        lon_deg = (lon_i * 180) / math.pi

        # Floor latitude to valid range [-90, 90]
        lat_deg = max(-90.0, min(90.0, lat_deg))

        # Normalize longitude to [-180, 180]
        # lon_deg = ((lon_deg + 180) % 360) - 180

        circle_points.append({"lat": lat_deg, "lon": lon_deg})

    # If the North Pole is included, do some corrective stuff
    if north_pole_included:
        # remove the first element from the list
        circle_points.pop(0)

        # manually add some corrective points
        circle_points.insert(0, {"lat": 90.0, "lon": circle_points[0]["lon"]})
        circle_points.append({"lat": 90.0, "lon": circle_points[-1]["lon"]})

    # If the South Pole is included, do some corrective stuff
    if south_pole_included:
        # find the index of the coord in the list with the lowest latitude
        min_lat_index = min(range(len(circle_points)), key=lambda idx: circle_points[idx]["lat"])

        # manually add correcting points so that the coverage is realistic
        circle_points.insert(
            min_lat_index + 1, {"lat": -90.0, "lon": circle_points[min_lat_index]["lon"]}
        )
        circle_points.insert(
            min_lat_index + 2, {"lat": -90.0, "lon": circle_points[min_lat_index + 2]["lon"]}
        )

    return circle_points
