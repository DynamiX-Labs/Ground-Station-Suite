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
Unit tests for satellite CRUD operations.
"""

import uuid

import pytest
from sqlalchemy import select

from crud.groups import add_satellite_group, fetch_satellite_group
from crud.satellites import (
    add_satellite,
    delete_satellite,
    edit_satellite,
    fetch_satellites,
    fetch_satellites_for_group_id,
    search_satellites,
)
from db.models import SatelliteOrbits

# TLE templates for testing (valid format but dummy data)
TLE1_TEMPLATE = "1 {norad:05d}U 00000A   21001.00000000  .00000000  00000-0  00000-0 0  9990"
TLE2_TEMPLATE = "2 {norad:05d}  51.0000 000.0000 0000000   0.0000   0.0000 15.00000000000000"


@pytest.mark.asyncio
class TestSatellitesCRUD:
    """Test suite for satellite CRUD operations."""

    async def test_add_satellite_success(self, db_session):
        """Test successful satellite creation."""
        satellite_data = {
            "name": "ISS (ZARYA)",
            "sat_id": "ISS-001",
            "norad_id": 25544,
            "status": "alive",
            "is_frequency_violator": False,
            "name_other": "International Space Station",
            "alternative_name": "ISS",
            "tle1": "1 25544U 98067A   21001.00000000  .00002182  00000-0  41420-4 0  9990",
            "tle2": "2 25544  51.6461 339.8014 0002571  34.5857  54.2426 15.48919393261778",
        }

        result = await add_satellite(db_session, satellite_data)

        assert result["success"] is True
        assert result["error"] is None
        assert result["data"]["name"] == "ISS (ZARYA)"
        assert result["data"]["norad_id"] == 25544
        assert result["data"]["source"] == "manual"
        assert result["data"]["status"] == "alive"
        assert "added" in result["data"]
        assert "updated" in result["data"]

    async def test_add_satellite_missing_required_field(self, db_session):
        """Test satellite creation fails without required fields."""
        satellite_data = {
            "name": "Test Satellite",
            "sat_id": "TEST-001",
            # Missing norad_id, status, is_frequency_violator, tle1, tle2
        }

        result = await add_satellite(db_session, satellite_data)

        assert result["success"] is False
        assert "Missing required field" in result["error"]

    async def test_fetch_satellites_all(self, db_session):
        """Test fetching all satellites."""
        # Add two satellites
        await add_satellite(
            db_session,
            {
                "name": "Satellite 1",
                "sat_id": "SAT-001",
                "norad_id": 11111,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=11111),
                "tle2": TLE2_TEMPLATE.format(norad=11111),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "Satellite 2",
                "sat_id": "SAT-002",
                "norad_id": 22222,
                "status": "dead",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=22222),
                "tle2": TLE2_TEMPLATE.format(norad=22222),
            },
        )

        result = await fetch_satellites(db_session, norad_id=None)

        assert result["success"] is True
        assert len(result["data"]) == 2

    async def test_fetch_satellite_by_norad_id(self, db_session):
        """Test fetching a single satellite by NORAD ID."""
        await add_satellite(
            db_session,
            {
                "name": "Test Satellite",
                "sat_id": "TEST-001",
                "norad_id": 99999,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=99999),
                "tle2": TLE2_TEMPLATE.format(norad=99999),
            },
        )

        result = await fetch_satellites(db_session, norad_id=99999)

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["norad_id"] == 99999

    async def test_fetch_satellites_by_list(self, db_session):
        """Test fetching multiple satellites by NORAD ID list."""
        await add_satellite(
            db_session,
            {
                "name": "Sat 1",
                "sat_id": "SAT-001",
                "norad_id": 11111,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=11111),
                "tle2": TLE2_TEMPLATE.format(norad=11111),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "Sat 2",
                "sat_id": "SAT-002",
                "norad_id": 22222,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=22222),
                "tle2": TLE2_TEMPLATE.format(norad=22222),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "Sat 3",
                "sat_id": "SAT-003",
                "norad_id": 33333,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=33333),
                "tle2": TLE2_TEMPLATE.format(norad=33333),
            },
        )

        result = await fetch_satellites(db_session, norad_id=[11111, 33333])

        assert result["success"] is True
        assert len(result["data"]) == 2
        norad_ids = [sat["norad_id"] for sat in result["data"]]
        assert 11111 in norad_ids
        assert 33333 in norad_ids
        assert 22222 not in norad_ids

    async def test_search_satellites_by_name(self, db_session):
        """Test searching satellites by name."""
        await add_satellite(
            db_session,
            {
                "name": "International Space Station",
                "sat_id": "ISS-001",
                "norad_id": 25544,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=25544),
                "tle2": TLE2_TEMPLATE.format(norad=25544),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "NOAA 19",
                "sat_id": "NOAA-19",
                "norad_id": 33591,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=33591),
                "tle2": TLE2_TEMPLATE.format(norad=33591),
            },
        )

        result = await search_satellites(db_session, keyword="space")

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["norad_id"] == 25544

    async def test_search_satellites_by_norad_id_partial(self, db_session):
        """Test searching satellites by partial NORAD ID."""
        await add_satellite(
            db_session,
            {
                "name": "Sat 1",
                "sat_id": "SAT-001",
                "norad_id": 12345,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=12345),
                "tle2": TLE2_TEMPLATE.format(norad=12345),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "Sat 2",
                "sat_id": "SAT-002",
                "norad_id": 12367,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=12367),
                "tle2": TLE2_TEMPLATE.format(norad=12367),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "Sat 3",
                "sat_id": "SAT-003",
                "norad_id": 99999,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=99999),
                "tle2": TLE2_TEMPLATE.format(norad=99999),
            },
        )

        result = await search_satellites(db_session, keyword="123")

        assert result["success"] is True
        assert len(result["data"]) == 2

    async def test_search_satellites_tokenized_prn_phrase(self, db_session):
        """Tokenized search should match constellation + PRN phrases across separated name tokens."""
        await add_satellite(
            db_session,
            {
                "name": "GPS BIII-1 (PRN 04)",
                "sat_id": "GPS-PRN04",
                "norad_id": 43873,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=43873),
                "tle2": TLE2_TEMPLATE.format(norad=43873),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "GALILEO FOC TEST (PRN 29)",
                "sat_id": "GAL-PRN29",
                "norad_id": 99929,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=99929),
                "tle2": TLE2_TEMPLATE.format(norad=99929),
            },
        )

        gps_result = await search_satellites(db_session, keyword="GPS PRN 04")
        assert gps_result["success"] is True
        assert any(sat["norad_id"] == 43873 for sat in gps_result["data"])

        gal_result = await search_satellites(db_session, keyword="Galileo PRN E29")
        assert gal_result["success"] is True
        assert any(sat["norad_id"] == 99929 for sat in gal_result["data"])

    async def test_search_satellites_all(self, db_session):
        """Test searching all satellites when no keyword provided."""
        await add_satellite(
            db_session,
            {
                "name": "Sat 1",
                "sat_id": "SAT-001",
                "norad_id": 11111,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=11111),
                "tle2": TLE2_TEMPLATE.format(norad=11111),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "Sat 2",
                "sat_id": "SAT-002",
                "norad_id": 22222,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=22222),
                "tle2": TLE2_TEMPLATE.format(norad=22222),
            },
        )

        result = await search_satellites(db_session, keyword=None)

        assert result["success"] is True
        assert len(result["data"]) == 2

    async def test_edit_satellite_success(self, db_session):
        """Test successful satellite editing."""
        await add_satellite(
            db_session,
            {
                "name": "Old Name",
                "sat_id": "OLD-001",
                "norad_id": 12345,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=12345),
                "tle2": TLE2_TEMPLATE.format(norad=12345),
            },
        )

        result = await edit_satellite(
            db_session, satellite_id=12345, name="New Name", status="dead"
        )

        assert result["success"] is True
        assert result["data"]["name"] == "New Name"
        assert result["data"]["status"] == "dead"
        assert result["data"]["norad_id"] == 12345

    async def test_edit_satellite_not_found(self, db_session):
        """Test editing non-existent satellite."""
        result = await edit_satellite(db_session, satellite_id=99999, name="New Name")

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_delete_satellite_success(self, db_session):
        """Test successful satellite deletion."""
        await add_satellite(
            db_session,
            {
                "name": "Test Satellite",
                "sat_id": "TEST-001",
                "norad_id": 12345,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=12345),
                "tle2": TLE2_TEMPLATE.format(norad=12345),
            },
        )

        result = await delete_satellite(db_session, satellite_id=12345)

        assert result["success"] is True

        # Verify deletion
        fetch_result = await fetch_satellites(db_session, norad_id=12345)
        assert len(fetch_result["data"]) == 0

    async def test_delete_satellite_removes_group_membership(self, db_session):
        """Deleting a satellite should also remove stale group references."""
        await add_satellite(
            db_session,
            {
                "name": "Group Member Satellite",
                "sat_id": "GROUP-001",
                "norad_id": 54321,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=54321),
                "tle2": TLE2_TEMPLATE.format(norad=54321),
            },
        )
        group_result = await add_satellite_group(
            db_session, {"name": "Artemis Test", "type": "user", "satellite_ids": [54321]}
        )
        group_id = group_result["data"]["id"]

        result = await delete_satellite(db_session, satellite_id=54321)

        assert result["success"] is True

        group_after_delete = await fetch_satellite_group(db_session, group_id)
        assert group_after_delete["success"] is True
        assert group_after_delete["data"]["satellite_ids"] == []

    async def test_delete_satellite_not_found(self, db_session):
        """Test deleting non-existent satellite."""
        result = await delete_satellite(db_session, satellite_id=99999)

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_search_satellites_with_groups(self, db_session):
        """Test that search includes group membership information."""
        # Add satellites
        await add_satellite(
            db_session,
            {
                "name": "ISS",
                "sat_id": "ISS-001",
                "norad_id": 25544,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": "1 25544U 98067A   21001.00000000  .00002182  00000-0  41420-4 0  9990",
                "tle2": "2 25544  51.6461 339.8014 0002571  34.5857  54.2426 15.48919393261778",
            },
        )

        # Add a group containing the satellite
        await add_satellite_group(
            db_session, {"name": "Manned Missions", "type": "user", "satellite_ids": [25544]}
        )

        result = await search_satellites(db_session, keyword="ISS")

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert "groups" in result["data"][0]
        assert len(result["data"][0]["groups"]) == 1
        assert result["data"][0]["groups"][0]["name"] == "Manned Missions"

    async def test_fetch_satellites_for_group_id(self, db_session):
        """Test fetching satellites by group ID."""
        # Add satellites
        await add_satellite(
            db_session,
            {
                "name": "Sat 1",
                "sat_id": "SAT-001",
                "norad_id": 11111,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=11111),
                "tle2": TLE2_TEMPLATE.format(norad=11111),
            },
        )
        await add_satellite(
            db_session,
            {
                "name": "Sat 2",
                "sat_id": "SAT-002",
                "norad_id": 22222,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=22222),
                "tle2": TLE2_TEMPLATE.format(norad=22222),
            },
        )

        # Add a group with both satellites
        group_result = await add_satellite_group(
            db_session, {"name": "Test Group", "type": "user", "satellite_ids": [11111, 22222]}
        )

        group_id = group_result["data"]["id"]

        # Fetch satellites for group
        result = await fetch_satellites_for_group_id(db_session, group_id)

        assert result["success"] is True
        assert len(result["data"]) == 2

    async def test_fetch_satellites_for_group_id_prunes_missing_members(self, db_session):
        """Fetching group satellites should remove stale NORAD IDs from group membership."""
        await add_satellite(
            db_session,
            {
                "name": "Sat 1",
                "sat_id": "SAT-001",
                "norad_id": 11111,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=11111),
                "tle2": TLE2_TEMPLATE.format(norad=11111),
            },
        )

        group_result = await add_satellite_group(
            db_session, {"name": "Stale Group", "type": "user", "satellite_ids": [11111, 99999]}
        )
        group_id = group_result["data"]["id"]

        result = await fetch_satellites_for_group_id(db_session, group_id)

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["norad_id"] == 11111

        group_after_fetch = await fetch_satellite_group(db_session, group_id)
        assert group_after_fetch["success"] is True
        assert group_after_fetch["data"]["satellite_ids"] == [11111]

    async def test_add_satellite_with_all_fields(self, db_session):
        """Test adding satellite with all optional fields."""
        satellite_data = {
            "name": "Full Satellite",
            "sat_id": "FULL-001",
            "norad_id": 99999,
            "status": "alive",
            "is_frequency_violator": False,
            "tle1": TLE1_TEMPLATE.format(norad=99999),
            "tle2": TLE2_TEMPLATE.format(norad=99999),
            "name_other": "Alternative Name",
            "alternative_name": "Another Name",
            "image": "http://example.com/image.jpg",
            "website": "http://example.com",
            "operator": "Test Operator",
            "countries": "USA, EU",
            "citation": "Test Citation",
            "associated_satellites": "12345, 67890",
        }

        result = await add_satellite(db_session, satellite_data)

        assert result["success"] is True
        assert result["data"]["operator"] == "Test Operator"
        assert result["data"]["countries"] == "USA, EU"
        assert result["data"]["website"] == "http://example.com"

    async def test_add_satellite_creates_canonical_earth_orbit(self, db_session):
        """Adding satellites should also upsert canonical earth orbit rows."""
        norad_id = 77889
        tle1 = TLE1_TEMPLATE.format(norad=norad_id)
        tle2 = TLE2_TEMPLATE.format(norad=norad_id)

        add_result = await add_satellite(
            db_session,
            {
                "name": "Orbit Seed Satellite",
                "sat_id": "ORBIT-001",
                "norad_id": norad_id,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": tle1,
                "tle2": tle2,
            },
        )

        assert add_result["success"] is True
        orbit_row = (
            await db_session.execute(
                select(SatelliteOrbits).where(
                    SatelliteOrbits.satellite_norad_id == norad_id,
                    SatelliteOrbits.central_body == "earth",
                )
            )
        ).scalar_one_or_none()
        assert orbit_row is not None
        assert orbit_row.model_kind == "tle"
        assert orbit_row.tle1 == tle1
        assert orbit_row.tle2 == tle2

    async def test_edit_satellite_updates_canonical_orbit_and_projects_fields(self, db_session):
        """Editing with orbit payload should update canonical orbit and fetch projection."""
        norad_id = 77901
        await add_satellite(
            db_session,
            {
                "name": "OMM Test Satellite",
                "sat_id": "ORBIT-002",
                "norad_id": norad_id,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": TLE1_TEMPLATE.format(norad=norad_id),
                "tle2": TLE2_TEMPLATE.format(norad=norad_id),
            },
        )

        updated_tle1 = "1 77901U 24001A   26010.50000000  .00001000  00000-0  10000-3 0  9992"
        updated_tle2 = "2 77901  97.4000 221.0000 0001000  30.0000 330.0000 14.90000000123456"

        edit_result = await edit_satellite(
            db_session,
            satellite_id=norad_id,
            orbit={
                "central_body": "earth",
                "model_kind": "omm",
                "tle1": updated_tle1,
                "tle2": updated_tle2,
                "omm_payload": {
                    "NORAD_CAT_ID": str(norad_id),
                    "OBJECT_NAME": "OMM Test Satellite",
                },
            },
        )

        assert edit_result["success"] is True
        orbit_row = (
            await db_session.execute(
                select(SatelliteOrbits).where(
                    SatelliteOrbits.satellite_norad_id == norad_id,
                    SatelliteOrbits.central_body == "earth",
                )
            )
        ).scalar_one_or_none()
        assert orbit_row is not None
        assert orbit_row.model_kind == "omm"
        assert orbit_row.tle1 == updated_tle1
        assert orbit_row.tle2 == updated_tle2
        assert isinstance(orbit_row.omm_payload, dict)
        assert orbit_row.omm_payload.get("NORAD_CAT_ID") == str(norad_id)

        fetched = await fetch_satellites(db_session, norad_id=norad_id)
        assert fetched["success"] is True
        assert len(fetched["data"]) == 1
        projected = fetched["data"][0]
        assert projected["orbit_format"] == "omm"
        assert projected["tle1"] == updated_tle1
        assert projected["tle2"] == updated_tle2
