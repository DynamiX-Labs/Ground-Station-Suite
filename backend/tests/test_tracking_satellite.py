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
Tests for tracking/satellite.py satellite position and path calculation functions.
"""

from datetime import datetime, timezone

import pytest

from tracking.satellite import (
    get_satellite_az_el,
    get_satellite_path,
    get_satellite_position_from_tle,
    normalize_longitude,
    split_at_dateline,
)


# Test fixtures
@pytest.fixture
def iss_tle():
    """ISS TLE data for testing (updated for 2025)."""
    return {
        "line1": "1 25544U 98067A   25001.50000000  .00012345  00000-0  21914-3 0  9999",
        "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.50000000999999",
        "name": "ISS (ZARYA)",
    }


@pytest.fixture
def iss_tle_lines():
    """ISS TLE as list of three lines (updated for 2025)."""
    return [
        "ISS (ZARYA)",
        "1 25544U 98067A   25001.50000000  .00012345  00000-0  21914-3 0  9999",
        "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.50000000999999",
    ]


@pytest.fixture
def iss_tle_two_lines():
    """ISS TLE as list of two lines (no name, updated for 2025)."""
    return [
        "1 25544U 98067A   25001.50000000  .00012345  00000-0  21914-3 0  9999",
        "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.50000000999999",
    ]


class TestGetSatelliteAzEl:
    """Test cases for get_satellite_az_el function."""

    def test_az_el_returns_tuple(self, iss_tle):
        """Test that function returns a tuple of two values."""
        observation_time = datetime(2023, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        result = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=observation_time,
        )

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_az_el_value_ranges(self, iss_tle):
        """Test that azimuth and elevation are within valid ranges."""
        observation_time = datetime(2023, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        azimuth, elevation = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=observation_time,
        )

        # Azimuth should be 0-360 degrees
        assert 0 <= azimuth < 360

        # Elevation should be -90 to 90 degrees
        assert -90 <= elevation <= 90

    def test_az_el_value_types(self, iss_tle):
        """Test that returned values are floats."""
        observation_time = datetime(2023, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        azimuth, elevation = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=observation_time,
        )

        assert isinstance(azimuth, float)
        assert isinstance(elevation, float)

    def test_az_el_precision(self, iss_tle):
        """Test that values are rounded to 4 decimal places."""
        observation_time = datetime(2023, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        azimuth, elevation = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=observation_time,
        )

        # Check that values have at most 4 decimal places
        assert len(str(azimuth).split(".")[-1]) <= 4
        assert len(str(elevation).split(".")[-1]) <= 4

    def test_az_el_different_times(self, iss_tle):
        """Test that different observation times produce different results."""
        time1 = datetime(2023, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        time2 = datetime(2023, 4, 19, 13, 0, 0, tzinfo=timezone.utc)

        az1, el1 = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=time1,
        )

        az2, el2 = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=time2,
        )

        # Satellite position should change over time
        assert (az1, el1) != (az2, el2)

    def test_az_el_different_locations(self, iss_tle):
        """Test that different observer locations produce different results."""
        observation_time = datetime(2023, 4, 19, 12, 0, 0, tzinfo=timezone.utc)

        # San Francisco
        az1, el1 = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=observation_time,
        )

        # London
        az2, el2 = get_satellite_az_el(
            home_lat=51.5074,
            home_lon=-0.1278,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=observation_time,
        )

        # Different locations should see different az/el
        assert (az1, el1) != (az2, el2)

    def test_az_el_consistency(self, iss_tle):
        """Test that same inputs produce same outputs."""
        observation_time = datetime(2023, 4, 19, 12, 0, 0, tzinfo=timezone.utc)

        result1 = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=observation_time,
        )

        result2 = get_satellite_az_el(
            home_lat=37.7749,
            home_lon=-122.4194,
            satellite_tle_line1=iss_tle["line1"],
            satellite_tle_line2=iss_tle["line2"],
            observation_time=observation_time,
        )

        assert result1 == result2


class TestGetSatellitePositionFromTle:
    """Test cases for get_satellite_position_from_tle function."""

    def test_position_returns_dict(self, iss_tle_lines):
        """Test that function returns a dictionary."""
        result = get_satellite_position_from_tle(iss_tle_lines)

        assert isinstance(result, dict)

    def test_position_has_required_fields(self, iss_tle_lines):
        """Test that returned dict has all required fields."""
        result = get_satellite_position_from_tle(iss_tle_lines)

        assert "lat" in result
        assert "lon" in result
        assert "alt" in result
        assert "vel" in result

    def test_position_field_types(self, iss_tle_lines):
        """Test that all fields are floats."""
        result = get_satellite_position_from_tle(iss_tle_lines)

        assert isinstance(result["lat"], float)
        assert isinstance(result["lon"], float)
        assert isinstance(result["alt"], float)
        assert isinstance(result["vel"], float)

    def test_position_lat_range(self, iss_tle_lines):
        """Test that latitude is within valid range."""
        result = get_satellite_position_from_tle(iss_tle_lines)

        # ISS has inclination ~51.6°, so latitude should be within ±52°
        assert -90 <= result["lat"] <= 90
        assert -52 <= result["lat"] <= 52

    def test_position_lon_range(self, iss_tle_lines):
        """Test that longitude is within valid range."""
        result = get_satellite_position_from_tle(iss_tle_lines)

        assert -180 <= result["lon"] <= 180

    def test_position_altitude_reasonable(self, iss_tle_lines):
        """Test that altitude is reasonable for ISS."""
        result = get_satellite_position_from_tle(iss_tle_lines)

        # ISS orbits around 400-420 km altitude
        assert 300000 < result["alt"] < 500000  # In meters

    def test_position_velocity_reasonable(self, iss_tle_lines):
        """Test that velocity is reasonable for ISS."""
        result = get_satellite_position_from_tle(iss_tle_lines)

        # ISS velocity is about 7.66 km/s
        assert 7.0 < result["vel"] < 8.5


class TestNormalizeLongitude:
    """Test cases for normalize_longitude function."""

    def test_normalize_within_range(self):
        """Test that values already in range are unchanged."""
        assert normalize_longitude(0.0) == 0.0
        assert normalize_longitude(90.0) == 90.0
        assert normalize_longitude(-90.0) == -90.0
        assert normalize_longitude(180.0) == 180.0
        assert normalize_longitude(-180.0) == -180.0

    def test_normalize_above_180(self):
        """Test normalizing values above 180."""
        assert normalize_longitude(270.0) == -90.0
        assert normalize_longitude(360.0) == 0.0
        assert normalize_longitude(450.0) == 90.0
        assert normalize_longitude(540.0) == 180.0

    def test_normalize_below_minus_180(self):
        """Test normalizing values below -180."""
        assert normalize_longitude(-270.0) == 90.0
        assert normalize_longitude(-360.0) == 0.0
        assert normalize_longitude(-450.0) == -90.0
        assert normalize_longitude(-540.0) == -180.0

    def test_normalize_large_positive(self):
        """Test normalizing large positive values."""
        assert normalize_longitude(720.0) == 0.0
        assert normalize_longitude(1080.0) == 0.0

    def test_normalize_large_negative(self):
        """Test normalizing large negative values."""
        assert normalize_longitude(-720.0) == 0.0
        assert normalize_longitude(-1080.0) == 0.0

    def test_normalize_edge_cases(self):
        """Test edge cases around ±180."""
        assert normalize_longitude(179.9) == 179.9
        assert normalize_longitude(-179.9) == -179.9
        assert normalize_longitude(180.1) == pytest.approx(-179.9, abs=0.1)


class TestSplitAtDateline:
    """Test cases for split_at_dateline function."""

    def test_split_empty_list(self):
        """Test splitting empty list."""
        result = split_at_dateline([])
        assert result == []

    def test_split_single_point(self):
        """Test splitting single point."""
        points = [{"lat": 0, "lon": 0}]
        result = split_at_dateline(points)

        assert len(result) == 1
        assert result[0] == points

    def test_split_no_crossing(self):
        """Test path that doesn't cross dateline."""
        points = [
            {"lat": 0, "lon": 0},
            {"lat": 10, "lon": 10},
            {"lat": 20, "lon": 20},
            {"lat": 30, "lon": 30},
        ]
        result = split_at_dateline(points)

        # Should return single segment
        assert len(result) == 1
        assert result[0] == points

    def test_split_simple_crossing(self):
        """Test path that crosses dateline once."""
        points = [
            {"lat": 0, "lon": 170},
            {"lat": 0, "lon": 175},
            {"lat": 0, "lon": -175},  # Crosses dateline
            {"lat": 0, "lon": -170},
        ]
        result = split_at_dateline(points)

        # Should split into two segments
        assert len(result) == 2
        assert len(result[0]) == 2  # First two points
        assert len(result[1]) == 2  # Last two points

    def test_split_multiple_crossings(self):
        """Test path that crosses dateline multiple times."""
        points = [
            {"lat": 0, "lon": 170},
            {"lat": 0, "lon": -170},  # Cross
            {"lat": 0, "lon": -175},
            {"lat": 0, "lon": 175},  # Cross back
            {"lat": 0, "lon": 170},
        ]
        result = split_at_dateline(points)

        # Should split into three segments
        assert len(result) == 3

    def test_split_westward_crossing(self):
        """Test westward crossing (positive to negative)."""
        points = [
            {"lat": 0, "lon": 179},
            {"lat": 0, "lon": -179},
        ]
        result = split_at_dateline(points)

        assert len(result) == 2

    def test_split_eastward_crossing(self):
        """Test eastward crossing (negative to positive)."""
        points = [
            {"lat": 0, "lon": -179},
            {"lat": 0, "lon": 179},
        ]
        result = split_at_dateline(points)

        assert len(result) == 2

    def test_split_preserves_point_order(self):
        """Test that splitting preserves point order within segments."""
        points = [
            {"lat": 0, "lon": 170},
            {"lat": 10, "lon": 175},
            {"lat": 20, "lon": -175},  # Cross
            {"lat": 30, "lon": -170},
        ]
        result = split_at_dateline(points)

        assert result[0][0] == points[0]
        assert result[0][1] == points[1]
        assert result[1][0] == points[2]
        assert result[1][1] == points[3]

    def test_split_threshold(self):
        """Test that split happens only when longitude difference > 180."""
        points = [
            {"lat": 0, "lon": 0},
            {"lat": 0, "lon": 180},  # Exactly 180 degrees - no split
            {"lat": 0, "lon": 0},
        ]
        result = split_at_dateline(points)

        # Should not split at exactly 180 degrees
        assert len(result) == 1


class TestGetSatellitePath:
    """Test cases for get_satellite_path function."""

    def test_path_returns_dict(self, iss_tle_two_lines):
        """Test that function returns a dictionary."""
        result = get_satellite_path(iss_tle_two_lines, duration_minutes=30)

        assert isinstance(result, dict)

    def test_path_has_required_keys(self, iss_tle_two_lines):
        """Test that returned dict has required keys."""
        result = get_satellite_path(iss_tle_two_lines, duration_minutes=30)

        assert "past" in result
        assert "future" in result

    def test_path_past_future_are_lists(self, iss_tle_two_lines):
        """Test that past and future are lists."""
        result = get_satellite_path(iss_tle_two_lines, duration_minutes=30)

        assert isinstance(result["past"], list)
        assert isinstance(result["future"], list)

    def test_path_segments_are_lists(self, iss_tle_two_lines):
        """Test that segments are lists of coordinate dicts."""
        result = get_satellite_path(iss_tle_two_lines, duration_minutes=30)

        if result["past"]:
            assert isinstance(result["past"][0], list)
            if result["past"][0]:
                assert "lat" in result["past"][0][0]
                assert "lon" in result["past"][0][0]

        if result["future"]:
            assert isinstance(result["future"][0], list)
            if result["future"][0]:
                assert "lat" in result["future"][0][0]
                assert "lon" in result["future"][0][0]

    def test_path_duration(self, iss_tle_two_lines):
        """Test path with different durations."""
        result_30 = get_satellite_path(iss_tle_two_lines, duration_minutes=30)
        result_60 = get_satellite_path(iss_tle_two_lines, duration_minutes=60)

        # Longer duration should have more points
        total_points_30 = sum(len(seg) for seg in result_30["past"] + result_30["future"])
        total_points_60 = sum(len(seg) for seg in result_60["past"] + result_60["future"])

        assert total_points_60 > total_points_30

    def test_path_step_size(self, iss_tle_two_lines):
        """Test path with different step sizes."""
        result_1min = get_satellite_path(iss_tle_two_lines, duration_minutes=30, step_minutes=1.0)
        result_5min = get_satellite_path(iss_tle_two_lines, duration_minutes=30, step_minutes=5.0)

        # Smaller step size should have more points
        total_points_1min = sum(len(seg) for seg in result_1min["past"] + result_1min["future"])
        total_points_5min = sum(len(seg) for seg in result_5min["past"] + result_5min["future"])

        assert total_points_1min > total_points_5min

    def test_path_coordinates_valid_range(self, iss_tle_two_lines):
        """Test that all coordinates are within valid ranges."""
        result = get_satellite_path(iss_tle_two_lines, duration_minutes=30)

        for segment in result["past"] + result["future"]:
            for point in segment:
                assert -90 <= point["lat"] <= 90
                assert -180 <= point["lon"] <= 180

    def test_path_invalid_tle_length(self):
        """Test that invalid TLE length is handled."""
        invalid_tle = ["single line"]
        result = get_satellite_path(invalid_tle, duration_minutes=30)

        # Should return empty result on error
        assert result["past"] == []
        assert result["future"] == []

    def test_path_zero_duration(self, iss_tle_two_lines):
        """Test path with zero duration."""
        result = get_satellite_path(iss_tle_two_lines, duration_minutes=0)

        # Should return minimal path (just current position)
        assert len(result["past"]) >= 0
        assert len(result["future"]) >= 0

    def test_path_small_duration(self, iss_tle_two_lines):
        """Test path with very small duration."""
        result = get_satellite_path(iss_tle_two_lines, duration_minutes=1, step_minutes=1.0)

        assert isinstance(result, dict)
        assert "past" in result
        assert "future" in result
