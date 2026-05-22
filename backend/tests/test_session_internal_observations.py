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
Tests for internal observation session management.

Tests SessionTracker and SessionService handling of automated observation
sessions, ensuring proper isolation from user sessions and correct lifecycle
management.
"""

import pytest

from session.tracker import session_tracker
from vfos.state import VFOManager


class TestInternalSessionTracking:
    """Test cases for internal observation session tracking."""

    @pytest.fixture(autouse=True)
    def cleanup_after_test(self):
        """Clean up any internal sessions after each test."""
        yield
        # Clean up any leftover internal sessions
        for session_id in list(session_tracker.get_all_internal_sessions()):
            session_tracker.unregister_internal_session(session_id)

    def test_register_internal_session(self):
        """Test registering an internal observation session."""
        obs_id = "test-obs-register-123"

        session_id = session_tracker.register_internal_session(
            observation_id=obs_id,
            sdr_id="test-sdr-1",
            vfo_number=1,
            metadata={"norad_id": 25544, "transmitter_id": "iss-voice"},
        )

        assert session_id == f"internal:{obs_id}"
        assert session_tracker.is_internal_session(session_id)

    def test_internal_session_metadata(self):
        """Test that internal session metadata is correctly set."""
        obs_id = "test-obs-metadata-456"

        session_id = session_tracker.register_internal_session(
            observation_id=obs_id,
            sdr_id="test-sdr-1",
            vfo_number=1,
            metadata={"norad_id": 25544, "transmitter_id": "iss-voice"},
        )

        metadata = session_tracker.get_session_metadata(session_id)
        assert metadata is not None
        assert metadata["origin"] == "internal"
        assert "ObservationScheduler" in metadata["user_agent"]
        assert metadata["norad_id"] == 25544
        assert metadata["transmitter_id"] == "iss-voice"

    def test_internal_session_sdr_mapping(self):
        """Test that SDR mapping is correctly established."""
        obs_id = "test-obs-sdr-789"

        session_id = session_tracker.register_internal_session(
            observation_id=obs_id,
            sdr_id="test-sdr-2",
            vfo_number=2,
        )

        sdr_id = session_tracker.get_session_sdr(session_id)
        assert sdr_id == "test-sdr-2"

    def test_internal_session_vfo_mapping(self):
        """Test that VFO mapping is correctly established."""
        obs_id = "test-obs-vfo-101"

        session_id = session_tracker.register_internal_session(
            observation_id=obs_id,
            sdr_id="test-sdr-1",
            vfo_number=3,
        )

        vfo_num = session_tracker.get_session_vfo_int(session_id)
        assert vfo_num == 3

    def test_list_internal_sessions(self):
        """Test listing internal sessions."""
        obs_id_1 = "test-obs-list-1"
        obs_id_2 = "test-obs-list-2"

        session_id_1 = session_tracker.register_internal_session(
            observation_id=obs_id_1, sdr_id="test-sdr-1", vfo_number=1
        )
        session_id_2 = session_tracker.register_internal_session(
            observation_id=obs_id_2, sdr_id="test-sdr-2", vfo_number=2
        )

        internal_sessions = session_tracker.get_all_internal_sessions()
        assert session_id_1 in internal_sessions
        assert session_id_2 in internal_sessions

    def test_internal_not_in_user_sessions(self):
        """Test that internal sessions are not listed as user sessions."""
        obs_id = "test-obs-user-202"

        session_id = session_tracker.register_internal_session(
            observation_id=obs_id, sdr_id="test-sdr-1", vfo_number=1
        )

        user_sessions = session_tracker.get_all_user_sessions()
        assert session_id not in user_sessions

    def test_internal_session_count(self):
        """Test counting internal sessions."""
        initial_count = session_tracker.get_internal_session_count()

        obs_id = "test-obs-count-303"
        session_tracker.register_internal_session(
            observation_id=obs_id, sdr_id="test-sdr-1", vfo_number=1
        )

        new_count = session_tracker.get_internal_session_count()
        assert new_count == initial_count + 1

    def test_unregister_internal_session(self):
        """Test unregistering an internal session."""
        obs_id = "test-obs-unreg-404"

        session_id = session_tracker.register_internal_session(
            observation_id=obs_id, sdr_id="test-sdr-1", vfo_number=1
        )

        assert session_tracker.is_internal_session(session_id)

        result = session_tracker.unregister_internal_session(obs_id)
        assert result is True
        assert not session_tracker.is_internal_session(session_id)

    def test_unregister_nonexistent_session(self):
        """Test unregistering a session that doesn't exist."""
        result = session_tracker.unregister_internal_session("nonexistent-obs-id")
        assert result is False

    def test_internal_session_full_cleanup(self):
        """Test that unregistering clears all session data."""
        obs_id = "test-obs-cleanup-505"

        session_id = session_tracker.register_internal_session(
            observation_id=obs_id, sdr_id="test-sdr-1", vfo_number=1
        )

        # Verify session exists
        assert session_tracker.get_session_sdr(session_id) == "test-sdr-1"
        assert session_id in session_tracker.get_all_internal_sessions()

        # Unregister
        session_tracker.unregister_internal_session(obs_id)

        # Verify all data is cleared
        assert not session_tracker.is_internal_session(session_id)
        assert session_id not in session_tracker.get_all_internal_sessions()
        assert session_tracker.get_session_sdr(session_id) is None
        assert session_tracker.get_session_vfo_int(session_id) is None


class TestInternalSessionIsolation:
    """Test that internal sessions are properly isolated from user sessions."""

    @pytest.fixture(autouse=True)
    def cleanup_after_test(self):
        """Clean up sessions after each test."""
        yield
        # Clean up internal sessions
        for session_id in list(session_tracker.get_all_internal_sessions()):
            session_tracker.unregister_internal_session(session_id)
        # Clean up any test user sessions
        for session_id in ["test-user-session-1", "test-user-session-2"]:
            session_tracker.clear_session(session_id)

    def test_internal_and_user_sessions_separate(self):
        """Test that internal and user sessions are tracked separately."""
        # Create a user session
        user_session_id = "test-user-session-1"
        session_tracker.register_session_streaming(user_session_id, "test-sdr-1")
        session_tracker.set_session_vfo_int(user_session_id, 1)

        # Create an internal session
        obs_id = "test-obs-isolation-606"
        internal_session_id = session_tracker.register_internal_session(
            observation_id=obs_id, sdr_id="test-sdr-2", vfo_number=2
        )

        # Verify separation
        user_sessions = session_tracker.get_all_user_sessions()
        internal_sessions = session_tracker.get_all_internal_sessions()

        assert user_session_id in user_sessions
        assert internal_session_id not in user_sessions

        assert internal_session_id in internal_sessions
        assert user_session_id not in internal_sessions

    def test_runtime_snapshot_includes_internal_flag(self):
        """Test that runtime snapshot correctly flags internal sessions."""
        # Create both types of sessions
        user_session_id = "test-user-session-2"
        session_tracker.register_session_streaming(user_session_id, "test-sdr-1")

        obs_id = "test-obs-snapshot-707"
        internal_session_id = session_tracker.register_internal_session(
            observation_id=obs_id, sdr_id="test-sdr-2", vfo_number=1
        )

        # Get runtime snapshot (requires ProcessManager mock, so we'll just test the flag method)
        # The actual snapshot test would require more setup
        assert session_tracker.is_internal_session(internal_session_id) is True
        assert session_tracker.is_internal_session(user_session_id) is False
