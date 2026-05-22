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
Unit tests for satellite group CRUD operations.
"""

import uuid

import pytest

from crud.groups import (
    add_satellite_group,
    delete_satellite_group,
    edit_satellite_group,
    fetch_satellite_group,
    fetch_system_satellite_group_by_identifier,
)


@pytest.mark.asyncio
class TestGroupsCRUD:
    """Test suite for satellite group CRUD operations."""

    async def test_add_satellite_group_success(self, db_session):
        """Test successful satellite group creation."""
        group_data = {
            "name": "Weather Satellites",
            "type": "user",
            "satellite_ids": [25338, 28654, 33591],
        }

        result = await add_satellite_group(db_session, group_data)

        assert result["success"] is True
        assert result["error"] is None
        assert result["data"]["name"] == "Weather Satellites"
        assert result["data"]["type"] == "user"
        assert len(result["data"]["satellite_ids"]) == 3
        assert "id" in result["data"]
        assert "added" in result["data"]

    async def test_add_satellite_group_with_identifier(self, db_session):
        """Test creating system group with identifier."""
        group_data = {
            "name": "Amateur Radio",
            "identifier": "amateur",
            "type": "system",
            "satellite_ids": [25544, 43017],
        }

        result = await add_satellite_group(db_session, group_data)

        assert result["success"] is True
        assert result["data"]["identifier"] == "amateur"
        assert result["data"]["type"] == "system"

    async def test_add_satellite_group_missing_name(self, db_session):
        """Test group creation fails without name."""
        group_data = {"type": "user", "satellite_ids": [25338]}

        result = await add_satellite_group(db_session, group_data)

        assert result["success"] is False
        assert "Name is required" in result["error"]

    async def test_fetch_all_satellite_groups(self, db_session):
        """Test fetching all satellite groups."""
        # Add multiple groups
        await add_satellite_group(
            db_session, {"name": "Group 1", "type": "user", "satellite_ids": [11111]}
        )
        await add_satellite_group(
            db_session, {"name": "Group 2", "type": "system", "satellite_ids": [22222]}
        )
        await add_satellite_group(
            db_session, {"name": "Group 3", "type": "user", "satellite_ids": [33333]}
        )

        result = await fetch_satellite_group(db_session)

        assert result["success"] is True
        assert len(result["data"]) == 3

    async def test_fetch_satellite_group_by_id(self, db_session):
        """Test fetching a single group by ID."""
        add_result = await add_satellite_group(
            db_session, {"name": "Test Group", "type": "user", "satellite_ids": [12345]}
        )

        group_id = add_result["data"]["id"]
        result = await fetch_satellite_group(db_session, group_id=group_id)

        assert result["success"] is True
        assert result["data"]["id"] == group_id
        assert result["data"]["name"] == "Test Group"

    async def test_fetch_satellite_groups_by_type(self, db_session):
        """Test fetching groups filtered by type."""
        # Add groups of different types
        await add_satellite_group(
            db_session, {"name": "User Group 1", "type": "user", "satellite_ids": [11111]}
        )
        await add_satellite_group(
            db_session, {"name": "System Group", "type": "system", "satellite_ids": [22222]}
        )
        await add_satellite_group(
            db_session, {"name": "User Group 2", "type": "user", "satellite_ids": [33333]}
        )

        # Fetch only user groups
        result = await fetch_satellite_group(db_session, group_type="user")

        assert result["success"] is True
        assert len(result["data"]) == 2
        for group in result["data"]:
            assert group["type"] == "user"

    async def test_fetch_satellite_group_by_id_and_type(self, db_session):
        """Test fetching a group by ID with type filter."""
        add_result = await add_satellite_group(
            db_session, {"name": "System Group", "type": "system", "satellite_ids": [12345]}
        )

        group_id = add_result["data"]["id"]

        # Fetch with correct type
        result = await fetch_satellite_group(db_session, group_id=group_id, group_type="system")
        assert result["success"] is True
        assert result["data"] is not None

        # Fetch with wrong type (should return None)
        result = await fetch_satellite_group(db_session, group_id=group_id, group_type="user")
        assert result["success"] is True
        assert result["data"] is None

    async def test_fetch_system_group_by_identifier_success(self, db_session):
        """Test fetching system group by identifier."""
        await add_satellite_group(
            db_session,
            {
                "name": "Amateur Radio",
                "identifier": "amateur",
                "type": "system",
                "satellite_ids": [25544, 43017],
            },
        )

        result = await fetch_system_satellite_group_by_identifier(db_session, "amateur")

        assert result["success"] is True
        assert result["data"]["identifier"] == "amateur"
        assert result["data"]["type"] == "system"
        assert result["data"]["name"] == "Amateur Radio"

    async def test_fetch_system_group_by_identifier_not_found(self, db_session):
        """Test fetching non-existent system group by identifier."""
        result = await fetch_system_satellite_group_by_identifier(db_session, "nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_fetch_system_group_ignores_user_groups(self, db_session):
        """Test that system group fetch ignores user groups with same identifier."""
        # Add a user group with identifier
        await add_satellite_group(
            db_session,
            {"name": "User Group", "identifier": "test", "type": "user", "satellite_ids": [11111]},
        )

        result = await fetch_system_satellite_group_by_identifier(db_session, "test")

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_edit_satellite_group_success(self, db_session):
        """Test successful satellite group editing."""
        add_result = await add_satellite_group(
            db_session, {"name": "Old Name", "type": "user", "satellite_ids": [11111, 22222]}
        )

        group_id = add_result["data"]["id"]

        # Edit the group
        edit_data = {"name": "New Name", "satellite_ids": [11111, 22222, 33333]}

        result = await edit_satellite_group(db_session, group_id, edit_data)

        assert result["success"] is True
        assert result["data"]["name"] == "New Name"
        assert len(result["data"]["satellite_ids"]) == 3
        assert 33333 in result["data"]["satellite_ids"]

    async def test_edit_satellite_group_not_found(self, db_session):
        """Test editing non-existent group."""
        fake_id = str(uuid.uuid4())

        result = await edit_satellite_group(db_session, fake_id, {"name": "New Name"})

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_edit_satellite_group_removes_id_from_data(self, db_session):
        """Test that edit operation removes 'id' from data dict."""
        add_result = await add_satellite_group(
            db_session, {"name": "Test Group", "type": "user", "satellite_ids": [11111]}
        )

        group_id = add_result["data"]["id"]

        # Try to edit with 'id' in data (should be ignored)
        edit_data = {"id": str(uuid.uuid4()), "name": "Updated Name"}  # Different ID

        result = await edit_satellite_group(db_session, group_id, edit_data)

        assert result["success"] is True
        assert result["data"]["id"] == group_id  # ID unchanged
        assert result["data"]["name"] == "Updated Name"

    async def test_delete_satellite_group_success(self, db_session):
        """Test successful group deletion."""
        add_result = await add_satellite_group(
            db_session, {"name": "Test Group", "type": "user", "satellite_ids": [12345]}
        )

        group_id = add_result["data"]["id"]

        # Delete the group
        result = await delete_satellite_group(db_session, [group_id])

        assert result["success"] is True

        # Verify deletion
        fetch_result = await fetch_satellite_group(db_session, group_id=group_id)
        assert fetch_result["data"] is None

    async def test_delete_multiple_satellite_groups(self, db_session):
        """Test deleting multiple groups at once."""
        group1 = await add_satellite_group(
            db_session, {"name": "Group 1", "type": "user", "satellite_ids": [11111]}
        )
        group2 = await add_satellite_group(
            db_session, {"name": "Group 2", "type": "user", "satellite_ids": [22222]}
        )

        group_ids = [group1["data"]["id"], group2["data"]["id"]]

        # Delete both
        result = await delete_satellite_group(db_session, group_ids)

        assert result["success"] is True

        # Verify both are deleted
        all_groups = await fetch_satellite_group(db_session)
        assert len(all_groups["data"]) == 0

    async def test_delete_satellite_group_not_found(self, db_session):
        """Test deleting non-existent group."""
        fake_id = str(uuid.uuid4())

        result = await delete_satellite_group(db_session, [fake_id])

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_satellite_group_empty_satellite_ids(self, db_session):
        """Test creating group with empty satellite list."""
        group_data = {"name": "Empty Group", "type": "user", "satellite_ids": []}

        result = await add_satellite_group(db_session, group_data)

        assert result["success"] is True
        assert result["data"]["satellite_ids"] == []

    async def test_satellite_group_null_satellite_ids(self, db_session):
        """Test creating group with null satellite_ids."""
        group_data = {
            "name": "Null Satellites Group",
            "type": "user",
            # No satellite_ids field
        }

        result = await add_satellite_group(db_session, group_data)

        assert result["success"] is True
        assert result["data"]["satellite_ids"] is None

    async def test_edit_satellite_group_change_type(self, db_session):
        """Test changing group type from user to system."""
        add_result = await add_satellite_group(
            db_session, {"name": "User Group", "type": "user", "satellite_ids": [11111]}
        )

        group_id = add_result["data"]["id"]

        # Change to system type
        result = await edit_satellite_group(
            db_session, group_id, {"type": "system", "identifier": "new_system"}
        )

        assert result["success"] is True
        assert result["data"]["type"] == "system"
        assert result["data"]["identifier"] == "new_system"
