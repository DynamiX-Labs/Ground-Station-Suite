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
Unit tests for tracking state CRUD operations.
"""

import uuid

import pytest

from crud.trackingstate import get_tracking_state, set_tracking_state


@pytest.mark.asyncio
class TestTrackingStateCRUD:
    """Test suite for tracking state CRUD operations."""

    async def test_set_tracking_state_new(self, db_session):
        """Test creating new tracking state."""
        tracking_data = {
            "name": "satellite-tracking",
            "value": {
                "norad_id": 25544,
                "rotator_state": "connected",
                "rig_state": "disconnected",
                "group_id": str(uuid.uuid4()),
                "rotator_id": str(uuid.uuid4()),
                "rig_id": str(uuid.uuid4()),
                "transmitter_id": "ABC123",
            },
        }

        result = await set_tracking_state(db_session, tracking_data)

        assert result["success"] is True
        assert result["data"]["name"] == "satellite-tracking"
        assert result["data"]["value"]["norad_id"] == 25544
        assert result["data"]["value"]["rotator_state"] == "connected"

    async def test_set_tracking_state_missing_name(self, db_session):
        """Test tracking state creation fails without name."""
        tracking_data = {"value": {"norad_id": 25544}}

        result = await set_tracking_state(db_session, tracking_data)

        assert result["success"] is False
        assert "name is required" in result["error"]

    async def test_set_tracking_state_missing_value(self, db_session):
        """Test tracking state creation fails without value."""
        tracking_data = {"name": "satellite-tracking"}

        result = await set_tracking_state(db_session, tracking_data)

        assert result["success"] is False
        assert "value is required" in result["error"]

    async def test_set_tracking_state_missing_required_fields(self, db_session):
        """Test new tracking state requires all fields."""
        tracking_data = {
            "name": "satellite-tracking",
            "value": {
                "norad_id": 25544
                # Missing required fields
            },
        }

        result = await set_tracking_state(db_session, tracking_data)

        assert result["success"] is False
        assert "required" in result["error"]

    async def test_set_tracking_state_new_without_group_id(self, db_session):
        """Automated observations may start tracking without a group_id."""
        tracking_data = {
            "name": "satellite-tracking:auto-observation",
            "value": {
                "norad_id": 25544,
                "rotator_state": "tracking",
                "rig_state": "disconnected",
                "rotator_id": str(uuid.uuid4()),
                "rig_id": "none",
                "transmitter_id": "none",
                "rig_vfo": "none",
                "vfo1": "uplink",
                "vfo2": "downlink",
            },
        }

        result = await set_tracking_state(db_session, tracking_data)

        assert result["success"] is True
        assert result["data"]["name"] == "satellite-tracking:auto-observation"
        assert result["data"]["value"]["norad_id"] == 25544
        assert "group_id" not in result["data"]["value"]

    async def test_set_tracking_state_new_mission_target_without_norad(self, db_session):
        """Mission trackers can be created without NORAD/group fields."""
        tracking_data = {
            "name": "satellite-tracking:mission-slot",
            "value": {
                "target_type": "mission",
                "command": "Voyager 1",
                "rotator_state": "disconnected",
                "rig_state": "stopped",
                "rotator_id": "none",
                "rig_id": "none",
                "transmitter_id": "none",
            },
        }

        result = await set_tracking_state(db_session, tracking_data)

        assert result["success"] is True
        assert result["data"]["name"] == "satellite-tracking:mission-slot"
        assert result["data"]["value"]["target_type"] == "mission"
        assert result["data"]["value"]["command"] == "Voyager 1"
        assert result["data"]["value"].get("norad_id") is None

    async def test_set_tracking_state_new_body_target_without_norad(self, db_session):
        """Body trackers can be created without NORAD/group fields."""
        tracking_data = {
            "name": "satellite-tracking:body-slot",
            "value": {
                "target_type": "body",
                "body_id": "mars",
                "rotator_state": "disconnected",
                "rig_state": "stopped",
                "rotator_id": "none",
                "rig_id": "none",
                "transmitter_id": "none",
            },
        }

        result = await set_tracking_state(db_session, tracking_data)

        assert result["success"] is True
        assert result["data"]["name"] == "satellite-tracking:body-slot"
        assert result["data"]["value"]["target_type"] == "body"
        assert result["data"]["value"]["body_id"] == "mars"
        assert result["data"]["value"].get("norad_id") is None

    async def test_set_tracking_state_update_existing(self, db_session):
        """Test updating existing tracking state."""
        # Create initial state
        initial_data = {
            "name": "satellite-tracking",
            "value": {
                "norad_id": 25544,
                "rotator_state": "connected",
                "rig_state": "disconnected",
                "group_id": str(uuid.uuid4()),
                "rotator_id": str(uuid.uuid4()),
                "rig_id": str(uuid.uuid4()),
                "transmitter_id": "ABC123",
            },
        }
        await set_tracking_state(db_session, initial_data)

        # Update with partial data (should merge)
        update_data = {
            "name": "satellite-tracking",
            "value": {"rotator_state": "disconnected", "new_field": "new_value"},
        }

        result = await set_tracking_state(db_session, update_data)

        assert result["success"] is True
        # Should have merged values
        assert result["data"]["value"]["norad_id"] == 25544  # Original value
        assert result["data"]["value"]["rotator_state"] == "disconnected"  # Updated
        assert result["data"]["value"]["new_field"] == "new_value"  # New field

    async def test_set_tracking_state_merge_behavior(self, db_session):
        """Test that updates merge with existing values."""
        # Create initial state
        initial_data = {
            "name": "test-state",
            "value": {
                "norad_id": 12345,
                "rotator_state": "connected",
                "rig_state": "connected",
                "group_id": "group-1",
                "rotator_id": "rotator-1",
                "rig_id": "rig-1",
            },
        }
        await set_tracking_state(db_session, initial_data)

        # Update only rig_state
        update_data = {"name": "test-state", "value": {"rig_state": "disconnected"}}

        result = await set_tracking_state(db_session, update_data)

        assert result["success"] is True
        # All original values should still be present
        assert result["data"]["value"]["norad_id"] == 12345
        assert result["data"]["value"]["rotator_state"] == "connected"
        assert result["data"]["value"]["rig_state"] == "disconnected"
        assert result["data"]["value"]["group_id"] == "group-1"

    async def test_get_tracking_state_success(self, db_session):
        """Test retrieving existing tracking state."""
        # Create state first
        tracking_data = {
            "name": "satellite-tracking",
            "value": {
                "norad_id": 25544,
                "rotator_state": "connected",
                "rig_state": "disconnected",
                "group_id": str(uuid.uuid4()),
                "rotator_id": str(uuid.uuid4()),
                "rig_id": str(uuid.uuid4()),
            },
        }
        await set_tracking_state(db_session, tracking_data)

        # Retrieve it
        result = await get_tracking_state(db_session, "satellite-tracking")

        assert result["success"] is True
        assert result["data"]["name"] == "satellite-tracking"
        assert result["data"]["value"]["norad_id"] == 25544

    async def test_get_tracking_state_not_found(self, db_session):
        """Test retrieving non-existent tracking state."""
        result = await get_tracking_state(db_session, "nonexistent")

        assert result["success"] is True
        assert result["data"] is None
        assert "not found" in result["error"]

    async def test_get_tracking_state_missing_name(self, db_session):
        """Test get tracking state fails without name."""
        result = await get_tracking_state(db_session, None)

        assert result["success"] is False
        assert "name is required" in result["error"]

    async def test_tracking_state_complex_value(self, db_session):
        """Test tracking state with complex nested data."""
        complex_data = {
            "name": "complex-tracking",
            "value": {
                "norad_id": 12345,
                "rotator_state": "connected",
                "rig_state": "connected",
                "group_id": "group-1",
                "rotator_id": "rotator-1",
                "rig_id": "rig-1",
                "settings": {"auto_track": True, "doppler_correction": True, "min_elevation": 10},
                "history": [
                    {"time": "2025-01-01T00:00:00", "event": "started"},
                    {"time": "2025-01-01T00:05:00", "event": "aos"},
                ],
            },
        }

        result = await set_tracking_state(db_session, complex_data)

        assert result["success"] is True
        assert result["data"]["value"]["settings"]["auto_track"] is True
        assert len(result["data"]["value"]["history"]) == 2

    async def test_tracking_state_multiple_instances(self, db_session):
        """Test multiple tracking state instances with different names."""
        # Create state for satellite tracking
        sat_data = {
            "name": "satellite-tracking",
            "value": {
                "norad_id": 25544,
                "rotator_state": "connected",
                "rig_state": "connected",
                "group_id": "g1",
                "rotator_id": "r1",
                "rig_id": "rig1",
            },
        }
        await set_tracking_state(db_session, sat_data)

        # Create state for map settings
        map_data = {
            "name": "map-settings",
            "value": {"zoom": 5, "center": [40, -74], "layer": "satellite"},
        }
        # Note: map-settings won't have required fields, so this should fail
        # unless we're updating an existing record
        result = await set_tracking_state(db_session, map_data)

        # This should fail due to missing required fields for new record
        assert result["success"] is False

    async def test_tracking_state_update_preserves_unmodified_fields(self, db_session):
        """Test that updating doesn't lose unmodified fields."""
        # Create initial state with many fields
        initial_data = {
            "name": "test-tracking",
            "value": {
                "norad_id": 99999,
                "rotator_state": "connected",
                "rig_state": "connected",
                "group_id": "group-1",
                "rotator_id": "rotator-1",
                "rig_id": "rig-1",
                "transmitter_id": "trans-1",
                "custom_field_1": "value1",
                "custom_field_2": "value2",
            },
        }
        await set_tracking_state(db_session, initial_data)

        # Update only one field
        update_data = {"name": "test-tracking", "value": {"custom_field_1": "updated_value1"}}

        result = await set_tracking_state(db_session, update_data)

        assert result["success"] is True
        # All original fields should still exist
        assert result["data"]["value"]["norad_id"] == 99999
        assert result["data"]["value"]["custom_field_2"] == "value2"
        # Updated field
        assert result["data"]["value"]["custom_field_1"] == "updated_value1"

    async def test_tracking_state_idempotent_updates(self, db_session):
        """Test that setting same value multiple times works correctly."""
        tracking_data = {
            "name": "idempotent-test",
            "value": {
                "norad_id": 12345,
                "rotator_state": "connected",
                "rig_state": "connected",
                "group_id": "g1",
                "rotator_id": "r1",
                "rig_id": "rig1",
            },
        }

        # Set it three times
        result1 = await set_tracking_state(db_session, tracking_data)
        result2 = await set_tracking_state(db_session, tracking_data)
        result3 = await set_tracking_state(db_session, tracking_data)

        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True

        # Final state should match
        final_result = await get_tracking_state(db_session, "idempotent-test")
        assert final_result["data"]["value"]["norad_id"] == 12345
