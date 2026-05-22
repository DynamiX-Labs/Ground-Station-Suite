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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from vfos.state import VFOManager


def test_vfo_defaults_include_voice_squelch_fields():
    manager = VFOManager()
    session_id = "test-vfo-defaults-squelch"

    try:
        vfo_state = manager.get_vfo_state(session_id, 1)
        assert vfo_state is not None
        assert vfo_state.squelch_mode == "carrier"
        assert vfo_state.vad_sensitivity == "medium"
        assert vfo_state.vad_close_delay_ms == 300
    finally:
        manager._session_vfo_states.pop(session_id, None)


def test_vfo_voice_squelch_fields_are_normalized_and_clamped():
    manager = VFOManager()
    session_id = "test-vfo-update-squelch"

    try:
        manager.update_vfo_state(
            session_id=session_id,
            vfo_id=1,
            squelch_mode="HYBRID",
            vad_sensitivity="HIGH",
            vad_close_delay_ms=900,
        )

        vfo_state = manager.get_vfo_state(session_id, 1)
        assert vfo_state is not None
        assert vfo_state.squelch_mode == "hybrid"
        assert vfo_state.vad_sensitivity == "high"
        assert vfo_state.vad_close_delay_ms == 500

        manager.update_vfo_state(
            session_id=session_id,
            vfo_id=1,
            vad_close_delay_ms=10,
        )

        vfo_state = manager.get_vfo_state(session_id, 1)
        assert vfo_state is not None
        assert vfo_state.vad_close_delay_ms == 50

        manager.update_vfo_state(
            session_id=session_id,
            vfo_id=1,
            squelch_mode="invalid",
            vad_sensitivity="invalid",
            vad_close_delay_ms="not-a-number",
        )

        vfo_state = manager.get_vfo_state(session_id, 1)
        assert vfo_state is not None
        assert vfo_state.squelch_mode == "hybrid"
        assert vfo_state.vad_sensitivity == "high"
        assert vfo_state.vad_close_delay_ms == 50
    finally:
        manager._session_vfo_states.pop(session_id, None)
