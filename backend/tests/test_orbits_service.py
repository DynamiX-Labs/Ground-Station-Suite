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

"""Unit tests for the orbit abstraction service."""

import pytest

from crud.satellites import add_satellite
from db.models import SatelliteOrbits
from orbits import (
    CentralBody,
    OrbitModelKind,
    OrbitServiceError,
    build_satellite_ephemeris_payload,
    get_orbit_state,
    get_propagation_input,
    get_propagation_input_for_object,
)
from orbits.service import orbit_service

LEGACY_SATELLITE = {
    "norad_id": 25544,
    "name": "ISS (ZARYA)",
    "tle1": "1 25544U 98067A   25001.50000000  .00012345  00000-0  21914-3 0  9999",
    "tle2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.50000000999999",
}


def test_get_propagation_input_from_legacy_tle_row():
    propagation_input = get_propagation_input(LEGACY_SATELLITE, central_body=CentralBody.EARTH)

    assert propagation_input.object_id == 25544
    assert propagation_input.model_kind == OrbitModelKind.TLE
    assert propagation_input.tle1.startswith("1 25544U")
    assert propagation_input.tle2.startswith("2 25544")


def test_get_propagation_input_from_omm_row_uses_compatibility_path():
    omm_row = dict(LEGACY_SATELLITE)
    omm_row["orbit_format"] = "omm"
    omm_row["orbit_payload"] = {"NORAD_CAT_ID": "25544"}

    propagation_input = get_propagation_input(omm_row, central_body=CentralBody.EARTH)

    assert propagation_input.object_id == 25544
    assert propagation_input.model_kind == OrbitModelKind.OMM
    assert propagation_input.tle1.startswith("1 25544U")
    assert propagation_input.tle2.startswith("2 25544")


def test_get_propagation_input_rejects_missing_tle_lines():
    invalid_row = {"norad_id": 25544, "name": "ISS", "orbit_format": "tle"}

    with pytest.raises(OrbitServiceError, match="Missing TLE data"):
        get_propagation_input(invalid_row, central_body=CentralBody.EARTH)


def test_build_satellite_ephemeris_payload_preserves_tracker_shape():
    payload = build_satellite_ephemeris_payload(LEGACY_SATELLITE, central_body=CentralBody.EARTH)

    assert payload == {
        "norad_id": 25544,
        "name": "ISS (ZARYA)",
        "tle1": LEGACY_SATELLITE["tle1"],
        "tle2": LEGACY_SATELLITE["tle2"],
    }


def test_get_orbit_state_rejects_non_earth_body_for_now():
    with pytest.raises(OrbitServiceError, match="not implemented yet"):
        get_orbit_state(LEGACY_SATELLITE, central_body=CentralBody.MARS)


@pytest.mark.asyncio
async def test_get_propagation_input_for_object_reads_canonical_orbit_row(db_session):
    await add_satellite(db_session, LEGACY_SATELLITE)
    await db_session.merge(
        SatelliteOrbits(
            satellite_norad_id=25544,
            central_body="earth",
            model_kind="omm",
            tle1="1 25544U 98067A   25002.50000000  .00020000  00000-0  30000-3 0  9999",
            tle2="2 25544  51.6416 248.0000 0006703 130.5360 325.0288 15.50010000999999",
            omm_payload={"NORAD_CAT_ID": "25544", "OBJECT_ID": "1998-067A"},
        )
    )
    await db_session.commit()

    propagation_input = await get_propagation_input_for_object(
        db_session, 25544, central_body=CentralBody.EARTH
    )

    assert propagation_input.model_kind == OrbitModelKind.OMM
    assert propagation_input.tle1.startswith("1 25544U")
    assert propagation_input.tle2.startswith("2 25544")


@pytest.mark.asyncio
async def test_get_orbit_state_from_db_falls_back_to_legacy_satellite_tle_when_no_orbit_row(
    db_session,
):
    await add_satellite(db_session, LEGACY_SATELLITE)
    orbit_state = await orbit_service.get_orbit_state(db_session, 25544, CentralBody.EARTH)

    assert orbit_state.model_kind == OrbitModelKind.TLE
    assert orbit_state.tle1 == LEGACY_SATELLITE["tle1"]
    assert orbit_state.tle2 == LEGACY_SATELLITE["tle2"]
