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
Unit tests for TLE sources CRUD operations.
"""

import uuid

import pytest

from crud.groups import add_satellite_group
from crud.satellites import add_satellite
from crud.tlesources import (
    add_satellite_tle_source,
    delete_satellite_tle_sources,
    edit_satellite_tle_source,
    fetch_satellite_tle_source,
)


@pytest.mark.asyncio
class TestTLESourcesCRUD:
    """Test suite for TLE sources CRUD operations."""

    async def test_add_tle_source_success(self, db_session):
        """Test successful TLE source creation."""
        tle_source_data = {
            "name": "Amateur Radio Satellites",
            "url": "https://example.com/amateur.txt",
            "format": "3le",
        }

        result = await add_satellite_tle_source(db_session, tle_source_data)

        assert result["success"] is True
        assert result["data"]["name"] == "Amateur Radio Satellites"
        assert result["data"]["url"] == "https://example.com/amateur.txt"
        assert result["data"]["format"] == "3le"
        assert "identifier" in result["data"]  # Random identifier generated
        assert len(result["data"]["identifier"]) == 16
        assert "id" in result["data"]

    async def test_add_tle_source_missing_name(self, db_session):
        """Test TLE source creation fails without name."""
        tle_source_data = {"url": "https://example.com/test.txt"}

        result = await add_satellite_tle_source(db_session, tle_source_data)

        assert result["success"] is False

    async def test_add_tle_source_missing_url(self, db_session):
        """Test TLE source creation fails without URL."""
        tle_source_data = {"name": "Test Source"}

        result = await add_satellite_tle_source(db_session, tle_source_data)

        assert result["success"] is False

    async def test_fetch_all_tle_sources(self, db_session):
        """Test fetching all TLE sources."""
        # Add multiple sources
        await add_satellite_tle_source(
            db_session, {"name": "Source 1", "url": "https://example.com/source1.txt"}
        )
        await add_satellite_tle_source(
            db_session, {"name": "Source 2", "url": "https://example.com/source2.txt"}
        )

        result = await fetch_satellite_tle_source(db_session)

        assert result["success"] is True
        assert len(result["data"]) == 2

    async def test_fetch_tle_source_by_id(self, db_session):
        """Test fetching a single TLE source by ID."""
        add_result = await add_satellite_tle_source(
            db_session, {"name": "Test Source", "url": "https://example.com/test.txt"}
        )

        source_id = add_result["data"]["id"]
        result = await fetch_satellite_tle_source(db_session, source_id)

        assert result["success"] is True
        assert result["data"]["id"] == source_id
        assert result["data"]["name"] == "Test Source"

    async def test_fetch_tle_source_not_found(self, db_session):
        """Test fetching non-existent TLE source."""
        result = await fetch_satellite_tle_source(db_session, 99999)

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_edit_tle_source_success(self, db_session):
        """Test successful TLE source editing."""
        add_result = await add_satellite_tle_source(
            db_session, {"name": "Old Name", "url": "https://example.com/old.txt"}
        )

        source_id = str(add_result["data"]["id"])

        # Edit the source
        edit_data = {"name": "New Name", "url": "https://example.com/new.txt"}

        result = await edit_satellite_tle_source(db_session, source_id, edit_data)

        assert result["success"] is True
        assert result["data"]["name"] == "New Name"
        assert result["data"]["url"] == "https://example.com/new.txt"

    async def test_edit_tle_source_not_found(self, db_session):
        """Test editing non-existent TLE source."""
        fake_id = str(uuid.uuid4())

        result = await edit_satellite_tle_source(db_session, fake_id, {"name": "New Name"})

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_edit_tle_source_removes_metadata(self, db_session):
        """Test that edit removes added/updated/id from data."""
        add_result = await add_satellite_tle_source(
            db_session, {"name": "Test Source", "url": "https://example.com/test.txt"}
        )

        source_id = str(add_result["data"]["id"])

        # Try to edit with metadata (should be ignored)
        edit_data = {
            "id": "fake-id",
            "name": "Updated Name",
            "added": "2020-01-01",
            "updated": "2020-01-01",
        }

        result = await edit_satellite_tle_source(db_session, source_id, edit_data)

        assert result["success"] is True
        assert result["data"]["name"] == "Updated Name"
        # ID should remain unchanged
        assert result["data"]["id"] == add_result["data"]["id"]

    async def test_delete_tle_source_simple(self, db_session):
        """Test deleting TLE source without associated data."""
        add_result = await add_satellite_tle_source(
            db_session, {"name": "Test Source", "url": "https://example.com/test.txt"}
        )

        source_id = str(add_result["data"]["id"])

        # Delete the source
        result = await delete_satellite_tle_sources(db_session, [source_id])

        assert result["success"] is True
        assert "Successfully deleted" in result["data"]

        # Verify deletion
        fetch_result = await fetch_satellite_tle_source(db_session, add_result["data"]["id"])
        assert fetch_result["success"] is False

    async def test_delete_tle_source_with_satellites_and_group(self, db_session):
        """Test deleting TLE source cascades to satellites and groups."""
        # Add TLE source
        tle_result = await add_satellite_tle_source(
            db_session, {"name": "Test Source", "url": "https://example.com/test.txt"}
        )
        identifier = tle_result["data"]["identifier"]

        # Add satellites
        await add_satellite(
            db_session,
            {
                "name": "Sat 1",
                "sat_id": "SAT-001",
                "norad_id": 11111,
                "status": "alive",
                "is_frequency_violator": False,
                "tle1": "1 11111U 00000A   21001.00000000  .00000000  00000-0  00000-0 0  9990",
                "tle2": "2 11111  51.0000 000.0000 0000000   0.0000   0.0000 15.00000000000000",
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
                "tle1": "1 22222U 00000A   21001.00000000  .00000000  00000-0  00000-0 0  9990",
                "tle2": "2 22222  51.0000 000.0000 0000000   0.0000   0.0000 15.00000000000000",
            },
        )

        # Add group with same identifier
        await add_satellite_group(
            db_session,
            {
                "name": "Test Group",
                "identifier": identifier,
                "type": "system",
                "satellite_ids": [11111, 22222],
            },
        )

        # Delete TLE source
        source_id = str(tle_result["data"]["id"])
        result = await delete_satellite_tle_sources(db_session, [source_id])

        assert result["success"] is True
        assert "deletion_summary" in result
        assert result["deletion_summary"][0]["satellites_deleted"] == 2
        assert result["deletion_summary"][0]["group_deleted"] is True

    async def test_delete_multiple_tle_sources(self, db_session):
        """Test deleting multiple TLE sources at once."""
        source1 = await add_satellite_tle_source(
            db_session, {"name": "Source 1", "url": "https://example.com/source1.txt"}
        )
        source2 = await add_satellite_tle_source(
            db_session, {"name": "Source 2", "url": "https://example.com/source2.txt"}
        )

        source_ids = [str(source1["data"]["id"]), str(source2["data"]["id"])]

        # Delete both
        result = await delete_satellite_tle_sources(db_session, source_ids)

        assert result["success"] is True
        assert "Successfully deleted 2 TLE source(s)" in result["data"]

    async def test_delete_tle_sources_not_found(self, db_session):
        """Test deleting non-existent TLE sources."""
        fake_id = str(uuid.uuid4())

        result = await delete_satellite_tle_sources(db_session, [fake_id])

        assert result["success"] is False
        assert "None of the Satellite TLE sources were found" in result["error"]

    async def test_delete_tle_sources_partial_not_found(self, db_session):
        """Test deleting mix of existing and non-existent sources."""
        # Add one real source
        real_source = await add_satellite_tle_source(
            db_session, {"name": "Real Source", "url": "https://example.com/real.txt"}
        )

        real_id = str(real_source["data"]["id"])
        fake_id = str(uuid.uuid4())

        # Try to delete both
        result = await delete_satellite_tle_sources(db_session, [real_id, fake_id])

        assert result["success"] is True
        assert "Successfully deleted 1 TLE source(s)" in result["data"]
        assert "not found" in result["data"]

    async def test_tle_source_default_format(self, db_session):
        """Test TLE source uses default format if not provided."""
        result = await add_satellite_tle_source(
            db_session,
            {
                "name": "Test Source",
                "url": "https://example.com/test.txt",
                # No format specified
            },
        )

        assert result["success"] is True
        # Should use default from model
        assert "format" in result["data"]

    async def test_add_tle_source_basic_auth_requires_credentials(self, db_session):
        """Test basic auth sources require username and password."""
        result = await add_satellite_tle_source(
            db_session,
            {
                "name": "Space-Track Source",
                "url": "https://www.space-track.org/basicspacedata/query/...",
                "auth_type": "basic",
                "username": "user_only",
                "norad_ids": [25544],
            },
        )

        assert result["success"] is False
        assert "requires username and password" in result["error"]

    async def test_add_tle_source_basic_auth_success(self, db_session):
        """Test basic auth source persists plain username/password values."""
        result = await add_satellite_tle_source(
            db_session,
            {
                "name": "Space-Track Source",
                "url": "https://www.space-track.org/basicspacedata/query/...",
                "format": "omm",
                "provider": "space_track",
                "adapter": "space_track_gp",
                "auth_type": "basic",
                "username": "test-user",
                "password": "test-pass",
                "norad_ids": [25544],
            },
        )

        assert result["success"] is True
        assert result["data"]["auth_type"] == "basic"
        assert result["data"]["username"] == "test-user"
        assert result["data"]["password"] == "test-pass"

    async def test_add_tle_source_maps_legacy_celestrak_provider(self, db_session):
        """Test legacy celestrak provider aliases to generic_http."""
        result = await add_satellite_tle_source(
            db_session,
            {
                "name": "Legacy CelesTrak",
                "url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
                "provider": "celestrak",
                "format": "3le",
            },
        )

        assert result["success"] is True
        assert result["data"]["provider"] == "generic_http"
        assert result["data"]["adapter"] == "http_3le"

    async def test_add_space_track_tle_source_requires_norad_ids(self, db_session):
        """Test Space-Track source creation requires NORAD IDs."""
        result = await add_satellite_tle_source(
            db_session,
            {
                "name": "Space-Track Amateur",
                "url": "https://www.space-track.org/basicspacedata/query/class/gp",
                "format": "omm",
                "provider": "space_track",
                "adapter": "space_track_gp",
                "query_mode": "url",
                "auth_type": "basic",
                "username": "test-user",
                "password": "test-pass",
            },
        )

        assert result["success"] is False
        assert "at least one NORAD ID" in result["error"]

    async def test_add_space_track_tle_source_normalizes_norad_ids(self, db_session):
        """Test Space-Track source persists normalized NORAD IDs and ignores group inputs."""
        result = await add_satellite_tle_source(
            db_session,
            {
                "name": "Space-Track Amateur",
                "url": "",
                "format": "omm",
                "provider": "space_track",
                "adapter": "http_omm",
                "query_mode": "group_norad",
                "group_id": str(uuid.uuid4()),
                "norad_ids": "25544,43017 25544\n57172",
                "auth_type": "basic",
                "username": "test-user",
                "password": "test-pass",
            },
        )

        assert result["success"] is True
        assert result["data"]["query_mode"] == "url"
        assert result["data"]["group_id"] is None
        assert result["data"]["adapter"] == "space_track_gp"
        assert result["data"]["url"] == "https://www.space-track.org/basicspacedata/query/class/gp"
        assert result["data"]["norad_ids"] == [25544, 43017, 57172]
