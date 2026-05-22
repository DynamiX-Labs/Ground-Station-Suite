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
Tests for tlesync/utils.py utility functions.
"""

from datetime import datetime, timezone

import pytest
import requests

from tlesync.utils import (
    create_final_success_message,
    create_initial_sync_state,
    create_progress_tracker,
    create_satellite_from_tle_data,
    detect_duplicate_satellites,
    get_norad_id_from_tle,
    get_norad_ids,
    get_satellite_by_norad_id,
    get_transmitter_info_by_norad_id,
    normalize_satellite_ids,
    parse_date,
    parse_norad_id_from_line1,
    resolve_sync_source_urls,
    simple_parse_3le,
    sync_fetch,
)


class TestParseNoradId:
    """Test cases for NORAD ID parsing functions."""

    def test_parse_norad_id_from_line1_iss(self):
        """Test parsing NORAD ID from ISS TLE line 1."""
        line1 = "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997"
        assert parse_norad_id_from_line1(line1) == 25544

    def test_parse_norad_id_from_line1_with_spaces(self):
        """Test parsing NORAD ID with leading spaces."""
        line1 = "1  1234U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997"
        assert parse_norad_id_from_line1(line1) == 1234

    def test_parse_norad_id_from_line1_five_digits(self):
        """Test parsing 5-digit NORAD ID."""
        line1 = "1 99999U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997"
        assert parse_norad_id_from_line1(line1) == 99999

    def test_get_norad_id_from_tle_with_name(self):
        """Test extracting NORAD ID from 3LE format with name."""
        tle = """ISS (ZARYA)
1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"""
        assert get_norad_id_from_tle(tle) == 25544

    def test_get_norad_id_from_tle_without_name(self):
        """Test extracting NORAD ID from 2LE format without name."""
        tle = """1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"""
        assert get_norad_id_from_tle(tle) == 25544

    def test_get_norad_id_from_tle_with_extra_whitespace(self):
        """Test extracting NORAD ID with extra whitespace."""
        tle = """

ISS (ZARYA)
1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537

        """
        assert get_norad_id_from_tle(tle) == 25544

    def test_get_norad_id_from_tle_invalid_format(self):
        """Test that invalid TLE format raises ValueError."""
        invalid_tle = "This is not a TLE"
        with pytest.raises(ValueError, match="A valid TLE first data line was not found"):
            get_norad_id_from_tle(invalid_tle)

    def test_get_norad_id_from_tle_empty_string(self):
        """Test that empty TLE raises ValueError."""
        with pytest.raises(ValueError):
            get_norad_id_from_tle("")

    def test_get_norad_id_from_tle_only_line2(self):
        """Test that TLE with only line 2 raises ValueError."""
        tle = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"
        with pytest.raises(ValueError):
            get_norad_id_from_tle(tle)


class TestCreateSatelliteFromTleData:
    """Test cases for creating Satellites objects from TLE data."""

    def test_create_satellite_sets_tlesync_source(self):
        sat = {
            "name": "ISS (ZARYA)",
            "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
            "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",
        }

        satellite = create_satellite_from_tle_data(sat, 25544)

        assert satellite.norad_id == 25544
        assert satellite.source == "tlesync"


class TestSimpleParse3le:
    """Test cases for 3LE parsing function."""

    def test_simple_parse_3le_single_satellite(self):
        """Test parsing a single satellite from 3LE format."""
        tle_data = """ISS (ZARYA)
1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"""

        result = simple_parse_3le(tle_data)

        assert len(result) == 1
        assert result[0]["name"] == "ISS (ZARYA)"
        assert result[0]["line1"].startswith("1 25544U")
        assert result[0]["line2"].startswith("2 25544")

    def test_simple_parse_3le_multiple_satellites(self):
        """Test parsing multiple satellites from 3LE format."""
        tle_data = """ISS (ZARYA)
1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537
NOAA 19
1 33591U 09005A   23109.12345678  .00000123  00000-0  12345-3 0  9998
2 33591  99.1234  12.3456 0012345  12.3456 347.7654 14.12345678123456"""

        result = simple_parse_3le(tle_data)

        assert len(result) == 2
        assert result[0]["name"] == "ISS (ZARYA)"
        assert result[1]["name"] == "NOAA 19"

    def test_simple_parse_3le_with_extra_whitespace(self):
        """Test parsing 3LE data with extra whitespace."""
        tle_data = """  ISS (ZARYA)
1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537  """

        result = simple_parse_3le(tle_data)

        assert len(result) == 1
        assert result[0]["name"] == "ISS (ZARYA)"

    def test_simple_parse_3le_empty_string(self):
        """Test parsing empty string."""
        result = simple_parse_3le("")
        assert result == []

    def test_simple_parse_3le_incomplete_set(self):
        """Test parsing incomplete TLE set (missing line 2)."""
        tle_data = """ISS (ZARYA)
1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997"""

        result = simple_parse_3le(tle_data)
        # Should return empty list or incomplete set
        assert len(result) == 0


class TestParseDateFunction:
    """Test cases for parse_date function."""

    def test_parse_date_with_z_suffix(self):
        """Test parsing ISO 8601 date with Z suffix."""
        date_str = "2023-10-04T12:34:56Z"
        result = parse_date(date_str)

        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 10
        assert result.day == 4
        assert result.hour == 12
        assert result.minute == 34
        assert result.second == 56

    def test_parse_date_with_timezone_offset(self):
        """Test parsing ISO 8601 date with timezone offset."""
        date_str = "2023-10-04T12:34:56+00:00"
        result = parse_date(date_str)

        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_parse_date_with_microseconds(self):
        """Test parsing ISO 8601 date with microseconds."""
        date_str = "2023-10-04T12:34:56.123456Z"
        result = parse_date(date_str)

        assert isinstance(result, datetime)
        assert result.microsecond == 123456

    def test_parse_date_different_timezone(self):
        """Test parsing ISO 8601 date with non-UTC timezone."""
        date_str = "2023-10-04T12:34:56+05:30"
        result = parse_date(date_str)

        assert isinstance(result, datetime)


class TestGetNoradIds:
    """Test cases for get_norad_ids function."""

    def test_get_norad_ids_single(self):
        """Test extracting NORAD IDs from single TLE object."""
        tle_objects = [
            {
                "name": "ISS (ZARYA)",
                "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
                "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",
            }
        ]

        result = get_norad_ids(tle_objects)

        assert result == [25544]

    def test_get_norad_ids_multiple(self):
        """Test extracting NORAD IDs from multiple TLE objects."""
        tle_objects = [
            {
                "name": "ISS",
                "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
                "line2": "2 25544...",
            },
            {
                "name": "NOAA 19",
                "line1": "1 33591U 09005A   23109.12345678  .00000123  00000-0  12345-3 0  9998",
                "line2": "2 33591...",
            },
            {
                "name": "HUBBLE",
                "line1": "1 20580U 90037B   23109.12345678  .00000123  00000-0  12345-3 0  9998",
                "line2": "2 20580...",
            },
        ]

        result = get_norad_ids(tle_objects)

        assert result == [25544, 33591, 20580]

    def test_get_norad_ids_empty_list(self):
        """Test extracting NORAD IDs from empty list."""
        result = get_norad_ids([])
        assert result == []


class TestNormalizeSatelliteIds:
    """Test cases for normalizing group satellite membership."""

    def test_normalize_satellite_ids_accepts_list(self):
        assert normalize_satellite_ids([25544, "43017", 25544, 0, "bad"]) == [25544, 43017]

    def test_normalize_satellite_ids_accepts_stringified_json(self):
        assert normalize_satellite_ids('[25544, "43017", 25544]') == [25544, 43017]

    def test_normalize_satellite_ids_rejects_invalid_value(self):
        assert normalize_satellite_ids("not-json") == []


class TestGetSatelliteByNoradId:
    """Test cases for get_satellite_by_norad_id function."""

    def test_get_satellite_by_norad_id_found(self):
        """Test finding satellite by NORAD ID."""
        satellites = [
            {"norad_cat_id": 25544, "name": "ISS"},
            {"norad_cat_id": 33591, "name": "NOAA 19"},
            {"norad_cat_id": 20580, "name": "HUBBLE"},
        ]

        result = get_satellite_by_norad_id(33591, satellites)

        assert result is not None
        assert result["name"] == "NOAA 19"

    def test_get_satellite_by_norad_id_not_found(self):
        """Test finding non-existent satellite."""
        satellites = [
            {"norad_cat_id": 25544, "name": "ISS"},
            {"norad_cat_id": 33591, "name": "NOAA 19"},
        ]

        result = get_satellite_by_norad_id(99999, satellites)

        assert result is None

    def test_get_satellite_by_norad_id_empty_list(self):
        """Test finding satellite in empty list."""
        result = get_satellite_by_norad_id(25544, [])
        assert result is None


class TestGetTransmitterInfoByNoradId:
    """Test cases for get_transmitter_info_by_norad_id function."""

    def test_get_transmitter_info_single(self):
        """Test finding single transmitter by NORAD ID."""
        transmitters = [
            {"norad_cat_id": 25544, "description": "VHF", "downlink_low": 145800000},
            {"norad_cat_id": 33591, "description": "APT", "downlink_low": 137100000},
        ]

        result = get_transmitter_info_by_norad_id(25544, transmitters)

        assert len(result) == 1
        assert result[0]["description"] == "VHF"

    def test_get_transmitter_info_multiple(self):
        """Test finding multiple transmitters for same satellite."""
        transmitters = [
            {"norad_cat_id": 25544, "description": "VHF", "downlink_low": 145800000},
            {"norad_cat_id": 25544, "description": "UHF", "downlink_low": 437800000},
            {"norad_cat_id": 33591, "description": "APT", "downlink_low": 137100000},
        ]

        result = get_transmitter_info_by_norad_id(25544, transmitters)

        assert len(result) == 2
        assert result[0]["description"] == "VHF"
        assert result[1]["description"] == "UHF"

    def test_get_transmitter_info_not_found(self):
        """Test finding transmitters for non-existent satellite."""
        transmitters = [{"norad_cat_id": 25544, "description": "VHF", "downlink_low": 145800000}]

        result = get_transmitter_info_by_norad_id(99999, transmitters)

        assert result == []


class TestCreateInitialSyncState:
    """Test cases for create_initial_sync_state function."""

    def test_create_initial_sync_state_structure(self):
        """Test that initial sync state has correct structure."""
        state = create_initial_sync_state()

        assert state["status"] == "inprogress"
        assert state["progress"] == 0
        assert state["message"] == "Starting satellite data synchronization"
        assert state["success"] is None
        assert "last_update" in state
        assert state["active_sources"] == []
        assert state["completed_sources"] == []
        assert state["errors"] == []

    def test_create_initial_sync_state_has_stats(self):
        """Test that initial sync state has stats structure."""
        state = create_initial_sync_state()

        assert "stats" in state
        assert state["stats"]["satellites_processed"] == 0
        assert state["stats"]["transmitters_processed"] == 0
        assert state["stats"]["groups_processed"] == 0

    def test_create_initial_sync_state_has_tracking(self):
        """Test that initial sync state has tracking structures."""
        state = create_initial_sync_state()

        assert "newly_added" in state
        assert state["newly_added"]["satellites"] == []
        assert state["newly_added"]["transmitters"] == []

        assert "removed" in state
        assert state["removed"]["satellites"] == []
        assert state["removed"]["transmitters"] == []

        assert "modified" in state
        assert state["modified"]["satellites"] == []
        assert state["modified"]["transmitters"] == []

    def test_create_initial_sync_state_timestamp_format(self):
        """Test that last_update is in ISO format."""
        state = create_initial_sync_state()

        # Should be able to parse the timestamp
        last_update = datetime.fromisoformat(state["last_update"])
        assert isinstance(last_update, datetime)


class TestCreateProgressTracker:
    """Test cases for create_progress_tracker function."""

    def test_progress_tracker_basic(self):
        """Test basic progress tracking functionality."""
        sync_state = {"progress": 0, "message": "", "last_update": ""}

        class MockStateManager:
            def set_state(self, state):
                pass

        progress_phases = {"phase1": 50, "phase2": 50}

        update_progress, completed_phases, highest_progress = create_progress_tracker(
            progress_phases, sync_state, MockStateManager()
        )

        # Update phase1 to 50% complete
        update_progress("phase1", 50, 100, "Working on phase 1")

        assert sync_state["progress"] == 25  # 50% of 50 weight
        assert sync_state["message"] == "Working on phase 1"

    def test_progress_tracker_monotonic(self):
        """Test that progress never decreases."""
        sync_state = {"progress": 0, "message": "", "last_update": ""}

        class MockStateManager:
            def set_state(self, state):
                pass

        progress_phases = {"phase1": 100}

        update_progress, completed_phases, highest_progress = create_progress_tracker(
            progress_phases, sync_state, MockStateManager()
        )

        # Set progress to 50
        update_progress("phase1", 50, 100)
        assert sync_state["progress"] == 50

        # Try to set lower progress
        update_progress("phase1", 30, 100)
        assert sync_state["progress"] == 50  # Should not decrease

    def test_progress_tracker_phase_completion(self):
        """Test marking phases as completed."""
        sync_state = {"progress": 0, "message": "", "last_update": ""}

        class MockStateManager:
            def set_state(self, state):
                pass

        progress_phases = {"phase1": 50, "phase2": 50}

        update_progress, completed_phases, highest_progress = create_progress_tracker(
            progress_phases, sync_state, MockStateManager()
        )

        # Complete phase1
        update_progress("phase1", 100, 100)
        completed_phases.add("phase1")

        # Start phase2
        update_progress("phase2", 50, 100)

        # Should be 50 (phase1 complete) + 25 (phase2 half done) = 75
        assert sync_state["progress"] == 75


class TestCreateFinalSuccessMessage:
    """Test cases for create_final_success_message function."""

    def test_final_success_message_basic(self):
        """Test basic success message generation."""
        sync_state = {
            "newly_added": {"satellites": [], "transmitters": []},
            "removed": {"satellites": [], "transmitters": []},
            "modified": {"satellites": [], "transmitters": []},
        }

        message = create_final_success_message(100, 50, sync_state)

        assert "Successfully synchronized 100 satellites and 50 transmitters" in message

    def test_final_success_message_with_new_items(self):
        """Test success message with newly added items."""
        sync_state = {
            "newly_added": {
                "satellites": [{"norad_id": 1}, {"norad_id": 2}],
                "transmitters": [{"uuid": "a"}, {"uuid": "b"}, {"uuid": "c"}],
            },
            "removed": {"satellites": [], "transmitters": []},
            "modified": {"satellites": [], "transmitters": []},
        }

        message = create_final_success_message(100, 50, sync_state)

        assert "New: 2 satellites, 3 transmitters" in message

    def test_final_success_message_with_modifications(self):
        """Test success message with modified items."""
        sync_state = {
            "newly_added": {"satellites": [], "transmitters": []},
            "removed": {"satellites": [], "transmitters": []},
            "modified": {
                "satellites": [{"norad_id": 1}],
                "transmitters": [{"uuid": "a"}, {"uuid": "b"}],
            },
        }

        message = create_final_success_message(100, 50, sync_state)

        assert "Modified: 1 satellites, 2 transmitters" in message

    def test_final_success_message_with_removals(self):
        """Test success message with removed items."""
        sync_state = {
            "newly_added": {"satellites": [], "transmitters": []},
            "removed": {"satellites": [{"norad_id": 1}, {"norad_id": 2}], "transmitters": []},
            "modified": {"satellites": [], "transmitters": []},
        }

        message = create_final_success_message(100, 50, sync_state)

        assert "Removed: 2 satellites, 0 transmitters" in message


class TestDetectDuplicateSatellites:
    """Test cases for detect_duplicate_satellites function."""

    def test_detect_duplicates_no_duplicates(self):
        """Test detection when there are no duplicates."""

        class MockLogger:
            def info(self, msg):
                pass

        celestrak_list = [
            {
                "name": "ISS",
                "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
                "line2": "2 25544...",
            },
            {
                "name": "NOAA 19",
                "line1": "1 33591U 09005A   23109.12345678  .00000123  00000-0  12345-3 0  9998",
                "line2": "2 33591...",
            },
        ]

        result = detect_duplicate_satellites(celestrak_list, MockLogger())

        assert result["duplicate_count"] == 0
        assert result["total_duplicates"] == 0
        assert len(result["deduplicated_list"]) == 2

    def test_detect_duplicates_with_duplicates(self):
        """Test detection when there are duplicates."""

        class MockLogger:
            def info(self, msg):
                pass

        celestrak_list = [
            {
                "name": "ISS (ZARYA)",
                "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
                "line2": "2 25544...",
            },
            {
                "name": "ISS",
                "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
                "line2": "2 25544...",
            },
            {
                "name": "NOAA 19",
                "line1": "1 33591U 09005A   23109.12345678  .00000123  00000-0  12345-3 0  9998",
                "line2": "2 33591...",
            },
        ]

        result = detect_duplicate_satellites(celestrak_list, MockLogger())

        assert result["duplicate_count"] == 1  # One unique satellite has duplicates
        assert result["total_duplicates"] == 1  # One duplicate entry
        assert len(result["deduplicated_list"]) == 2  # Should have 2 unique satellites

    def test_detect_duplicates_multiple_names(self):
        """Test that duplicate detection tracks different names."""

        class MockLogger:
            def info(self, msg):
                pass

        celestrak_list = [
            {
                "name": "ISS (ZARYA)",
                "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
                "line2": "2 25544...",
            },
            {
                "name": "ISS",
                "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
                "line2": "2 25544...",
            },
            {
                "name": "INTERNATIONAL SPACE STATION",
                "line1": "1 25544U 98067A   23109.65481637  .00012345  00000-0  21914-3 0  9997",
                "line2": "2 25544...",
            },
        ]

        result = detect_duplicate_satellites(celestrak_list, MockLogger())

        assert result["duplicate_count"] == 1
        assert result["total_duplicates"] == 2
        # Check that all three names are tracked
        assert len(result["duplicates_info"][25544]["names"]) == 3


class TestSyncFetch:
    """Test cases for sync_fetch function."""

    def test_sync_fetch_success(self, monkeypatch):
        """Test successful fetch."""

        class MockResponse:
            status_code = 200
            text = "success"

        def mock_get(url, timeout):
            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)

        result = sync_fetch("http://example.com")

        assert result is not None
        assert result.status_code == 200

    def test_sync_fetch_timeout(self, monkeypatch):
        """Test fetch with timeout."""

        def mock_get(url, timeout):
            raise requests.Timeout()

        monkeypatch.setattr(requests, "get", mock_get)

        with pytest.raises(requests.Timeout):
            sync_fetch("http://example.com")


class TestResolveSyncSourceUrls:
    """Test URL normalization for configurable TLE sync metadata sources."""

    def test_none_uses_default(self):
        assert resolve_sync_source_urls(None, "http://default") == ["http://default"]

    def test_empty_list_uses_default(self):
        assert resolve_sync_source_urls([], "http://default") == ["http://default"]

    def test_string_uses_single_source(self):
        assert resolve_sync_source_urls("http://custom", "http://default") == ["http://custom"]

    def test_list_filters_invalid_entries(self):
        value = ["http://one", "", "  ", 123, "http://two"]
        assert resolve_sync_source_urls(value, "http://default") == ["http://one", "http://two"]
