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

"""Orbit service package."""

from .service import (
    CentralBody,
    OrbitModelKind,
    OrbitServiceError,
    OrbitState,
    PropagationInput,
    UnsupportedOrbitConfigurationError,
    build_satellite_ephemeris_payload,
    get_orbit_state,
    get_orbit_state_for_object,
    get_propagation_input,
    get_propagation_input_for_object,
    orbit_service,
)

__all__ = [
    "CentralBody",
    "OrbitModelKind",
    "OrbitServiceError",
    "OrbitState",
    "PropagationInput",
    "UnsupportedOrbitConfigurationError",
    "build_satellite_ephemeris_payload",
    "get_orbit_state",
    "get_orbit_state_for_object",
    "get_propagation_input",
    "get_propagation_input_for_object",
    "orbit_service",
]
