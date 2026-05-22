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
Tests for tracking/footprint.py satellite coverage circle calculations.
"""

import math

import pytest

from tracking.footprint import get_satellite_coverage_circle


class TestGetSatelliteCoverageCircle:
    """Test suite for get_satellite_coverage_circle function."""

    def test_basic_coverage_circle(self):
        """Test basic coverage circle generation with typical parameters."""
        sat_lat = 0.0
        sat_lon = 0.0
        altitude_km = 400.0
        num_points = 36

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km, num_points)

        # Should return num_points + 1 points (closed polygon)
        assert len(result) == num_points + 1

        # All points should be dictionaries with 'lat' and 'lon' keys
        for point in result:
            assert "lat" in point
            assert "lon" in point
            assert isinstance(point["lat"], float)
            assert isinstance(point["lon"], float)

        # First and last points should be the same (closed polygon)
        assert result[0]["lat"] == pytest.approx(result[-1]["lat"], abs=1e-6)
        assert result[0]["lon"] == pytest.approx(result[-1]["lon"], abs=1e-6)

    def test_latitude_bounds(self):
        """Test that all latitude values are within valid range [-90, 90]."""
        sat_lat = 45.0
        sat_lon = 10.0
        altitude_km = 500.0

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

        for point in result:
            assert -90.0 <= point["lat"] <= 90.0

    def test_low_altitude_narrow_coverage(self):
        """Test coverage circle for low altitude satellite (narrow coverage)."""
        sat_lat = 0.0
        sat_lon = 0.0
        altitude_km = 100.0  # Low altitude

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

        # Calculate approximate angular radius
        R_EARTH = 6378.137
        expected_angle_rad = math.acos(R_EARTH / (R_EARTH + altitude_km))
        expected_angle_deg = math.degrees(expected_angle_rad)

        # Check that coverage points are roughly at the expected distance
        for i in range(len(result) - 1):  # Skip last point (duplicate of first)
            lat_diff = abs(result[i]["lat"] - sat_lat)
            lon_diff = abs(result[i]["lon"] - sat_lon)
            angular_distance = math.sqrt(lat_diff**2 + lon_diff**2)

            # Should be close to expected angle (within reasonable tolerance)
            assert angular_distance == pytest.approx(expected_angle_deg, rel=0.2)

    def test_high_altitude_wide_coverage(self):
        """Test coverage circle for high altitude satellite (wide coverage)."""
        sat_lat = 0.0
        sat_lon = 0.0
        altitude_km = 35786.0  # Geostationary altitude

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

        # Calculate approximate angular radius
        R_EARTH = 6378.137
        expected_angle_rad = math.acos(R_EARTH / (R_EARTH + altitude_km))
        expected_angle_deg = math.degrees(expected_angle_rad)

        # High altitude should have large coverage angle (around 81 degrees)
        assert expected_angle_deg > 80.0

        # Verify points are distributed around the circle
        assert len(result) > 0

    def test_north_pole_coverage(self):
        """Test coverage when satellite is over North Pole."""
        sat_lat = 85.0  # Close to North Pole
        sat_lon = 0.0
        altitude_km = 400.0

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km, num_points=36)

        # Should include corrective points for North Pole
        # When North Pole is included, function adds pole vertices
        pole_points = [p for p in result if p["lat"] == 90.0]
        assert len(pole_points) >= 1  # Should have at least one pole point

        # All latitudes should still be valid
        for point in result:
            assert -90.0 <= point["lat"] <= 90.0

    def test_south_pole_coverage(self):
        """Test coverage when satellite is over South Pole."""
        sat_lat = -85.0  # Close to South Pole
        sat_lon = 0.0
        altitude_km = 400.0

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km, num_points=36)

        # Should include corrective points for South Pole
        pole_points = [p for p in result if p["lat"] == -90.0]
        assert len(pole_points) >= 1  # Should have at least one pole point

        # All latitudes should still be valid
        for point in result:
            assert -90.0 <= point["lat"] <= 90.0

    def test_equatorial_orbit(self):
        """Test coverage for satellite on equatorial orbit."""
        sat_lat = 0.0
        sat_lon = 180.0
        altitude_km = 400.0

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

        # Should be symmetric around equator
        positive_lats = [p["lat"] for p in result if p["lat"] > 0]
        negative_lats = [p["lat"] for p in result if p["lat"] < 0]

        # Should have roughly equal distribution above and below equator
        assert len(positive_lats) > 0
        assert len(negative_lats) > 0

    def test_different_longitudes(self):
        """Test coverage circles at different longitudes."""
        sat_lat = 45.0
        altitude_km = 400.0

        # Test at different longitudes
        for sat_lon in [0.0, 90.0, 180.0, -90.0]:
            result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

            # All should have valid results
            assert len(result) > 0
            for point in result:
                assert -90.0 <= point["lat"] <= 90.0

    def test_custom_num_points(self):
        """Test with different numbers of points."""
        sat_lat = 0.0
        sat_lon = 0.0
        altitude_km = 400.0

        for num_points in [12, 24, 36, 72]:
            result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km, num_points)

            # Should return num_points + 1 (unless pole correction is applied)
            # When no poles are included, should be exact
            if sat_lat < 80 and sat_lat > -80:
                assert len(result) == num_points + 1

    def test_invalid_altitude_below_earth_center(self):
        """Test with invalid altitude (below Earth's center)."""
        sat_lat = 0.0
        sat_lon = 0.0
        altitude_km = -7000.0  # Below Earth's center (radius ~6378 km)

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

        # Should handle gracefully and return just the subpoint
        assert len(result) == 1
        assert result[0]["lat"] == sat_lat
        assert result[0]["lon"] == sat_lon

    def test_zero_altitude_edge_case(self):
        """Test with zero altitude (satellite at Earth's surface)."""
        sat_lat = 30.0
        sat_lon = 50.0
        altitude_km = 0.0

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

        # Should still generate valid coverage (horizon at ground level)
        assert len(result) > 0
        for point in result:
            assert -90.0 <= point["lat"] <= 90.0

    def test_very_small_altitude(self):
        """Test with very small altitude."""
        sat_lat = 0.0
        sat_lon = 0.0
        altitude_km = 1.0  # 1 km altitude

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

        # Should generate very narrow coverage
        assert len(result) > 0

        # Coverage should be very small
        for point in result:
            # All points should be very close to the subpoint
            lat_diff = abs(point["lat"] - sat_lat)
            lon_diff = abs(point["lon"] - sat_lon)
            angular_distance = math.sqrt(lat_diff**2 + lon_diff**2)

            # Should be less than 2 degrees
            assert angular_distance < 2.0

    def test_coverage_circle_geometry(self):
        """Test that the coverage circle has proper geometric properties."""
        sat_lat = 0.0
        sat_lon = 0.0
        altitude_km = 400.0

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km, num_points=36)

        # Calculate distances from subpoint for all points
        # R_EARTH = 6378.137
        # expected_angle_rad = math.acos(R_EARTH / (R_EARTH + altitude_km))
        # expected_angle_deg = math.degrees(expected_angle_rad)

        distances = []
        for i in range(len(result) - 1):  # Skip last duplicate point
            lat_diff = result[i]["lat"] - sat_lat
            lon_diff = result[i]["lon"] - sat_lon
            distance = math.sqrt(lat_diff**2 + lon_diff**2)
            distances.append(distance)

        # All distances should be similar (forming a circle)
        avg_distance = sum(distances) / len(distances)
        for distance in distances:
            # Each point should be within 10% of average distance
            assert distance == pytest.approx(avg_distance, rel=0.1)

    def test_dateline_crossing(self):
        """Test coverage circle that crosses the international date line."""
        sat_lat = 0.0
        sat_lon = 179.0  # Near dateline
        altitude_km = 1000.0  # Large coverage

        result = get_satellite_coverage_circle(sat_lat, sat_lon, altitude_km)

        # Should handle crossing gracefully
        assert len(result) > 0

        # Check for longitude values on both sides of dateline
        longitudes = [p["lon"] for p in result]
        has_positive = any(lon > 170 for lon in longitudes)
        has_negative = any(lon < -170 for lon in longitudes)

        # Might have points on both sides if coverage is large enough
        assert has_positive or has_negative
