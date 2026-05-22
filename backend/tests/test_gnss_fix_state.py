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

from pipeline.orchestration.gnssfix import derive_gnss_fix_status_from_output, gnss_fix_stream_key


class TestDeriveGnssFixStatusFromOutput:
    def test_prefers_explicit_backend_status(self):
        assert derive_gnss_fix_status_from_output({"gnss_fix_status": "fix"}) == "FIX"
        assert derive_gnss_fix_status_from_output({"gnss_fix_status": "NO FIX"}) == "NO FIX"

    def test_detects_fix_from_coordinates(self):
        status = derive_gnss_fix_status_from_output(
            {"event": "tracking", "latitude": 37.9838, "longitude": 23.7275}
        )
        assert status == "FIX"

    def test_detects_fix_from_fix_quality(self):
        assert (
            derive_gnss_fix_status_from_output({"event": "nmea_gga", "fix_quality": "1"}) == "FIX"
        )

    def test_detects_no_fix_from_nmea_zero_quality(self):
        assert (
            derive_gnss_fix_status_from_output({"event": "nmea_gga", "fix_quality": "0"})
            == "NO FIX"
        )

    def test_detects_no_fix_from_nmea_without_fix_fields(self):
        assert derive_gnss_fix_status_from_output({"event": "nmea"}) == "NO FIX"

    def test_returns_none_without_fix_signal_fields(self):
        assert (
            derive_gnss_fix_status_from_output({"event": "acquisition", "message": "acq ok"})
            is None
        )

    def test_ignores_gnss_activity_heartbeat_for_fix_state(self):
        assert (
            derive_gnss_fix_status_from_output(
                {"event": "gnss_activity", "has_pvt": True, "udp_packets_per_sec": 1500}
            )
            is None
        )


class TestGnssFixStreamKey:
    def test_uses_session_and_vfo(self):
        assert gnss_fix_stream_key({"session_id": "abc", "vfo": 2}) == ("abc", "2")

    def test_handles_missing_fields(self):
        assert gnss_fix_stream_key({}) == ("", "")
