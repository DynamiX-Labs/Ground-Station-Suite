# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Offline solar-system state generation utilities.

This module computes heliocentric ecliptic coordinates for major planets using
analytic Keplerian elements (J2000 + linear drift terms), fully offline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import atan2, cos, pi, sin, sqrt
from typing import Dict, List, Tuple, cast


def _normalize_angle_deg(deg: float) -> float:
    return deg % 360.0


def _solve_kepler(mean_anomaly_rad: float, eccentricity: float) -> float:
    """Solve Kepler's equation E - e*sin(E) = M with Newton iterations."""
    ecc_anomaly = mean_anomaly_rad
    for _ in range(12):
        f_val = ecc_anomaly - eccentricity * sin(ecc_anomaly) - mean_anomaly_rad
        f_der = 1.0 - eccentricity * cos(ecc_anomaly)
        if abs(f_der) < 1e-12:
            break
        next_val = ecc_anomaly - f_val / f_der
        if abs(next_val - ecc_anomaly) < 1e-12:
            ecc_anomaly = next_val
            break
        ecc_anomaly = next_val
    return ecc_anomaly


# Elements from the classic low-precision formula set (degrees, AU) as a function
# of d = days from J2000. Good for visualization and fully offline operation.
_PLANET_ELEMENTS: Dict[str, Dict[str, float]] = {
    "mercury": {
        "N0": 48.3313,
        "N1": 3.24587e-5,
        "i0": 7.0047,
        "i1": 5.0e-8,
        "w0": 29.1241,
        "w1": 1.01444e-5,
        "a0": 0.387098,
        "a1": 0.0,
        "e0": 0.205635,
        "e1": 5.59e-10,
        "M0": 168.6562,
        "M1": 4.0923344368,
    },
    "venus": {
        "N0": 76.6799,
        "N1": 2.46590e-5,
        "i0": 3.3946,
        "i1": 2.75e-8,
        "w0": 54.8910,
        "w1": 1.38374e-5,
        "a0": 0.723330,
        "a1": 0.0,
        "e0": 0.006773,
        "e1": -1.302e-9,
        "M0": 48.0052,
        "M1": 1.6021302244,
    },
    "earth": {
        "N0": 0.0,
        "N1": 0.0,
        "i0": 0.0,
        "i1": 0.0,
        "w0": 282.9404,
        "w1": 4.70935e-5,
        "a0": 1.0,
        "a1": 0.0,
        "e0": 0.016709,
        "e1": -1.151e-9,
        "M0": 356.0470,
        "M1": 0.9856002585,
    },
    "mars": {
        "N0": 49.5574,
        "N1": 2.11081e-5,
        "i0": 1.8497,
        "i1": -1.78e-8,
        "w0": 286.5016,
        "w1": 2.92961e-5,
        "a0": 1.523688,
        "a1": 0.0,
        "e0": 0.093405,
        "e1": 2.516e-9,
        "M0": 18.6021,
        "M1": 0.5240207766,
    },
    "jupiter": {
        "N0": 100.4542,
        "N1": 2.76854e-5,
        "i0": 1.3030,
        "i1": -1.557e-7,
        "w0": 273.8777,
        "w1": 1.64505e-5,
        "a0": 5.20256,
        "a1": 0.0,
        "e0": 0.048498,
        "e1": 4.469e-9,
        "M0": 19.8950,
        "M1": 0.0830853001,
    },
    "saturn": {
        "N0": 113.6634,
        "N1": 2.38980e-5,
        "i0": 2.4886,
        "i1": -1.081e-7,
        "w0": 339.3939,
        "w1": 2.97661e-5,
        "a0": 9.55475,
        "a1": 0.0,
        "e0": 0.055546,
        "e1": -9.499e-9,
        "M0": 316.9670,
        "M1": 0.0334442282,
    },
    "uranus": {
        "N0": 74.0005,
        "N1": 1.3978e-5,
        "i0": 0.7733,
        "i1": 1.9e-8,
        "w0": 96.6612,
        "w1": 3.0565e-5,
        "a0": 19.18171,
        "a1": -1.55e-8,
        "e0": 0.047318,
        "e1": 7.45e-9,
        "M0": 142.5905,
        "M1": 0.011725806,
    },
    "neptune": {
        "N0": 131.7806,
        "N1": 3.0173e-5,
        "i0": 1.7700,
        "i1": -2.55e-7,
        "w0": 272.8461,
        "w1": -6.027e-6,
        "a0": 30.05826,
        "a1": 3.313e-8,
        "e0": 0.008606,
        "e1": 2.15e-9,
        "M0": 260.2471,
        "M1": 0.005995147,
    },
}

_AU_IN_KM = 149597870.7
_EARTH_RADIUS_KM = 6378.1366
_EARTH_RADIUS_IN_AU = _EARTH_RADIUS_KM / _AU_IN_KM
_JUPITER_RADIUS_KM = 71492.0
_JUPITER_RADIUS_IN_AU = _JUPITER_RADIUS_KM / _AU_IN_KM
_SATURN_RADIUS_KM = 60268.0
_SATURN_RADIUS_IN_AU = _SATURN_RADIUS_KM / _AU_IN_KM
_MOON_ORBIT_PERIOD_DAYS = 27.321661
_JUPITER_MOONS: Dict[str, Dict[str, float | str]] = {
    "io": {
        "name": "Io",
        "semi_major_axis_jupiter_radii": 5.905,
        "period_days": 1.769,
        "phase_offset": 0.0,
    },
    "europa": {
        "name": "Europa",
        "semi_major_axis_jupiter_radii": 9.397,
        "period_days": 3.551,
        "phase_offset": 1.4,
    },
    "ganymede": {
        "name": "Ganymede",
        "semi_major_axis_jupiter_radii": 14.989,
        "period_days": 7.155,
        "phase_offset": 2.7,
    },
    "callisto": {
        "name": "Callisto",
        "semi_major_axis_jupiter_radii": 26.364,
        "period_days": 16.689,
        "phase_offset": 4.1,
    },
}
_SATURN_MOONS: Dict[str, Dict[str, float | str]] = {
    "enceladus": {
        "name": "Enceladus",
        "semi_major_axis_saturn_radii": 3.949,
        "period_days": 1.370,
        "phase_offset": 0.5,
    },
    "rhea": {
        "name": "Rhea",
        "semi_major_axis_saturn_radii": 8.742,
        "period_days": 4.518,
        "phase_offset": 1.8,
    },
    "titan": {
        "name": "Titan",
        "semi_major_axis_saturn_radii": 20.273,
        "period_days": 15.945,
        "phase_offset": 2.9,
    },
    "iapetus": {
        "name": "Iapetus",
        "semi_major_axis_saturn_radii": 59.091,
        "period_days": 79.3215,
        "phase_offset": 4.4,
    },
}


def _days_since_j2000(epoch: datetime) -> float:
    utc_epoch = epoch.astimezone(timezone.utc)
    j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return (utc_epoch - j2000).total_seconds() / 86400.0


def _planet_state(name: str, day_offset: float) -> Dict[str, object]:
    elem = _PLANET_ELEMENTS[name]

    n_deg = elem["N0"] + elem["N1"] * day_offset
    i_deg = elem["i0"] + elem["i1"] * day_offset
    w_deg = elem["w0"] + elem["w1"] * day_offset
    a_au = elem["a0"] + elem["a1"] * day_offset
    e_val = elem["e0"] + elem["e1"] * day_offset
    m_deg = _normalize_angle_deg(elem["M0"] + elem["M1"] * day_offset)

    m_rad = m_deg * pi / 180.0
    n_rad = n_deg * pi / 180.0
    i_rad = i_deg * pi / 180.0
    w_rad = w_deg * pi / 180.0

    ecc_anomaly = _solve_kepler(m_rad, e_val)

    x_orb = a_au * (cos(ecc_anomaly) - e_val)
    y_orb = a_au * sqrt(max(0.0, 1.0 - e_val * e_val)) * sin(ecc_anomaly)

    true_anomaly = atan2(y_orb, x_orb)
    radius = sqrt(x_orb * x_orb + y_orb * y_orb)

    x_helio = radius * (
        cos(n_rad) * cos(true_anomaly + w_rad) - sin(n_rad) * sin(true_anomaly + w_rad) * cos(i_rad)
    )
    y_helio = radius * (
        sin(n_rad) * cos(true_anomaly + w_rad) + cos(n_rad) * sin(true_anomaly + w_rad) * cos(i_rad)
    )
    z_helio = radius * (sin(true_anomaly + w_rad) * sin(i_rad))

    # These legacy Earth elements describe the Sun's geocentric vector in the
    # classic low-precision formula set. Convert to Earth's heliocentric vector
    # so downstream geocentric subtraction (target - earth) has the correct sign.
    if name == "earth":
        x_helio = -x_helio
        y_helio = -y_helio
        z_helio = -z_helio

    phase = (true_anomaly % (2.0 * pi)) / (2.0 * pi)

    return {
        "name": name.capitalize(),
        "id": name,
        "body_type": "planet",
        "position_xyz_au": [x_helio, y_helio, z_helio],
        "orbital_elements": {
            "semi_major_axis_au": a_au,
            "eccentricity": e_val,
            "inclination_deg": i_deg,
            "longitude_ascending_node_deg": _normalize_angle_deg(n_deg),
            "argument_perihelion_deg": _normalize_angle_deg(w_deg),
            "mean_anomaly_deg": m_deg,
            "true_anomaly_deg": _normalize_angle_deg(true_anomaly * 180.0 / pi),
        },
        "phase": phase,
    }


def _velocity_from_finite_difference(name: str, day_offset: float) -> List[float]:
    delta_days = 1.0 / 1440.0
    prev_pos = _body_position_au(name, day_offset - delta_days)
    next_pos = _body_position_au(name, day_offset + delta_days)

    return [
        (next_pos[0] - prev_pos[0]) / (2.0 * delta_days),
        (next_pos[1] - prev_pos[1]) / (2.0 * delta_days),
        (next_pos[2] - prev_pos[2]) / (2.0 * delta_days),
    ]


def _moon_geocentric_position_au(day_offset: float) -> List[float]:
    """Compute low-precision Moon geocentric ecliptic position in AU."""
    n_deg = 125.1228 - 0.0529538083 * day_offset
    i_deg = 5.1454
    w_deg = 318.0634 + 0.1643573223 * day_offset
    a_earth_radii = 60.2666
    e_val = 0.0549
    m_deg = _normalize_angle_deg(115.3654 + 13.0649929509 * day_offset)

    m_rad = m_deg * pi / 180.0
    n_rad = n_deg * pi / 180.0
    i_rad = i_deg * pi / 180.0
    w_rad = w_deg * pi / 180.0

    ecc_anomaly = _solve_kepler(m_rad, e_val)
    x_orb = a_earth_radii * (cos(ecc_anomaly) - e_val)
    y_orb = a_earth_radii * sqrt(max(0.0, 1.0 - e_val * e_val)) * sin(ecc_anomaly)

    true_anomaly = atan2(y_orb, x_orb)
    radius_earth_radii = sqrt(x_orb * x_orb + y_orb * y_orb)

    x_geo = radius_earth_radii * (
        cos(n_rad) * cos(true_anomaly + w_rad) - sin(n_rad) * sin(true_anomaly + w_rad) * cos(i_rad)
    )
    y_geo = radius_earth_radii * (
        sin(n_rad) * cos(true_anomaly + w_rad) + cos(n_rad) * sin(true_anomaly + w_rad) * cos(i_rad)
    )
    z_geo = radius_earth_radii * (sin(true_anomaly + w_rad) * sin(i_rad))

    scale = _EARTH_RADIUS_IN_AU
    return [x_geo * scale, y_geo * scale, z_geo * scale]


def _jupiter_moon_jovicentric_position_au(moon_id: str, day_offset: float) -> List[float]:
    moon = _JUPITER_MOONS[moon_id]
    radius_au = cast(float, moon["semi_major_axis_jupiter_radii"]) * _JUPITER_RADIUS_IN_AU
    period_days = cast(float, moon["period_days"])
    phase_offset = cast(float, moon["phase_offset"])
    phase = (2.0 * pi * (day_offset / period_days)) + phase_offset
    return [radius_au * cos(phase), radius_au * sin(phase), 0.0]


def _saturn_moon_saturncentric_position_au(moon_id: str, day_offset: float) -> List[float]:
    moon = _SATURN_MOONS[moon_id]
    radius_au = cast(float, moon["semi_major_axis_saturn_radii"]) * _SATURN_RADIUS_IN_AU
    period_days = cast(float, moon["period_days"])
    phase_offset = cast(float, moon["phase_offset"])
    phase = (2.0 * pi * (day_offset / period_days)) + phase_offset
    return [radius_au * cos(phase), radius_au * sin(phase), 0.0]


def _body_position_au(name: str, day_offset: float) -> List[float]:
    if name == "sun":
        return [0.0, 0.0, 0.0]
    if name == "moon":
        earth_state = _planet_state("earth", day_offset)
        earth_pos = cast(List[float], earth_state["position_xyz_au"])
        moon_geo = _moon_geocentric_position_au(day_offset)
        return [
            earth_pos[0] + moon_geo[0],
            earth_pos[1] + moon_geo[1],
            earth_pos[2] + moon_geo[2],
        ]
    if name in _JUPITER_MOONS:
        jupiter_state = _planet_state("jupiter", day_offset)
        jupiter_pos = cast(List[float], jupiter_state["position_xyz_au"])
        moon_jovi = _jupiter_moon_jovicentric_position_au(name, day_offset)
        return [
            jupiter_pos[0] + moon_jovi[0],
            jupiter_pos[1] + moon_jovi[1],
            jupiter_pos[2] + moon_jovi[2],
        ]
    if name in _SATURN_MOONS:
        saturn_state = _planet_state("saturn", day_offset)
        saturn_pos = cast(List[float], saturn_state["position_xyz_au"])
        moon_saturn = _saturn_moon_saturncentric_position_au(name, day_offset)
        return [
            saturn_pos[0] + moon_saturn[0],
            saturn_pos[1] + moon_saturn[1],
            saturn_pos[2] + moon_saturn[2],
        ]

    state = _planet_state(name, day_offset)
    return cast(List[float], state["position_xyz_au"])


def _orbit_samples(name: str, day_offset: float, samples: int = 128) -> List[List[float]]:
    a_au = _PLANET_ELEMENTS[name]["a0"]
    orbital_period_days = max(10.0, 365.25 * (a_au**1.5))
    points: List[List[float]] = []
    for idx in range(samples):
        fraction = idx / float(samples)
        sample_day = day_offset + (fraction - 0.5) * orbital_period_days
        sample_state = _planet_state(name, sample_day)
        points.append(cast(List[float], sample_state["position_xyz_au"]))
    return points


def _moon_orbit_samples(day_offset: float, samples: int = 96) -> List[List[float]]:
    """Render a lunar orbit ring around Earth's current heliocentric position."""
    earth_now = _body_position_au("earth", day_offset)
    points: List[List[float]] = []
    for idx in range(samples):
        fraction = idx / float(samples)
        sample_day = day_offset + (fraction - 0.5) * _MOON_ORBIT_PERIOD_DAYS
        moon_geo = _moon_geocentric_position_au(sample_day)
        points.append(
            [
                earth_now[0] + moon_geo[0],
                earth_now[1] + moon_geo[1],
                earth_now[2] + moon_geo[2],
            ]
        )
    return points


def _jupiter_moon_orbit_samples(
    moon_id: str, day_offset: float, samples: int = 96
) -> List[List[float]]:
    """Render a moon orbit ring around Jupiter's current heliocentric position."""
    jupiter_now = _body_position_au("jupiter", day_offset)
    period_days = cast(float, _JUPITER_MOONS[moon_id]["period_days"])
    points: List[List[float]] = []
    for idx in range(samples):
        fraction = idx / float(samples)
        sample_day = day_offset + (fraction - 0.5) * period_days
        moon_jovi = _jupiter_moon_jovicentric_position_au(moon_id, sample_day)
        points.append(
            [
                jupiter_now[0] + moon_jovi[0],
                jupiter_now[1] + moon_jovi[1],
                jupiter_now[2] + moon_jovi[2],
            ]
        )
    return points


def _saturn_moon_orbit_samples(
    moon_id: str, day_offset: float, samples: int = 96
) -> List[List[float]]:
    """Render a moon orbit ring around Saturn's current heliocentric position."""
    saturn_now = _body_position_au("saturn", day_offset)
    period_days = cast(float, _SATURN_MOONS[moon_id]["period_days"])
    points: List[List[float]] = []
    for idx in range(samples):
        fraction = idx / float(samples)
        sample_day = day_offset + (fraction - 0.5) * period_days
        moon_saturn = _saturn_moon_saturncentric_position_au(moon_id, sample_day)
        points.append(
            [
                saturn_now[0] + moon_saturn[0],
                saturn_now[1] + moon_saturn[1],
                saturn_now[2] + moon_saturn[2],
            ]
        )
    return points


def compute_solar_system_snapshot(
    epoch: datetime,
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    """Compute offline solar-system positions and metadata at a specific epoch."""
    day_offset = _days_since_j2000(epoch)
    planets: List[Dict[str, object]] = []

    for planet_id in _PLANET_ELEMENTS:
        state = _planet_state(planet_id, day_offset)
        state["velocity_xyz_au_per_day"] = _velocity_from_finite_difference(planet_id, day_offset)
        state["orbit_samples_xyz_au"] = _orbit_samples(planet_id, day_offset)
        planets.append(state)

    moon_pos = _body_position_au("moon", day_offset)
    planets.append(
        {
            "name": "Moon",
            "id": "moon",
            "body_type": "moon",
            "parent_id": "earth",
            "position_xyz_au": moon_pos,
            "velocity_xyz_au_per_day": _velocity_from_finite_difference("moon", day_offset),
            "orbit_samples_xyz_au": _moon_orbit_samples(day_offset),
            "orbital_elements": {
                "semi_major_axis_au": 60.2666 * _EARTH_RADIUS_IN_AU,
                "eccentricity": 0.0549,
                "inclination_deg": 5.1454,
                "period_days": _MOON_ORBIT_PERIOD_DAYS,
            },
            "phase": None,
        }
    )

    for moon_id, moon in _JUPITER_MOONS.items():
        planets.append(
            {
                "name": cast(str, moon["name"]),
                "id": moon_id,
                "body_type": "moon",
                "parent_id": "jupiter",
                "position_xyz_au": _body_position_au(moon_id, day_offset),
                "velocity_xyz_au_per_day": _velocity_from_finite_difference(moon_id, day_offset),
                "orbit_samples_xyz_au": _jupiter_moon_orbit_samples(moon_id, day_offset),
                "orbital_elements": {
                    "semi_major_axis_au": cast(float, moon["semi_major_axis_jupiter_radii"])
                    * _JUPITER_RADIUS_IN_AU,
                    "period_days": cast(float, moon["period_days"]),
                },
                "phase": None,
            }
        )

    for moon_id, moon in _SATURN_MOONS.items():
        planets.append(
            {
                "name": cast(str, moon["name"]),
                "id": moon_id,
                "body_type": "moon",
                "parent_id": "saturn",
                "position_xyz_au": _body_position_au(moon_id, day_offset),
                "velocity_xyz_au_per_day": _velocity_from_finite_difference(moon_id, day_offset),
                "orbit_samples_xyz_au": _saturn_moon_orbit_samples(moon_id, day_offset),
                "orbital_elements": {
                    "semi_major_axis_au": cast(float, moon["semi_major_axis_saturn_radii"])
                    * _SATURN_RADIUS_IN_AU,
                    "period_days": cast(float, moon["period_days"]),
                },
                "phase": None,
            }
        )

    body_type_counts: Dict[str, int] = {}
    for body in planets:
        body_type = str(body.get("body_type") or "unknown")
        body_type_counts[body_type] = body_type_counts.get(body_type, 0) + 1

    meta: Dict[str, object] = {
        "source": "offline-analytic-kepler",
        "reference": "J2000 low-precision orbital elements",
        "epoch_utc": epoch.astimezone(timezone.utc).isoformat(),
        "body_type_counts": body_type_counts,
    }

    return meta, planets


def compute_body_position_heliocentric_au(body_id: str, epoch: datetime) -> List[float]:
    """Compute heliocentric ecliptic position for one supported body at epoch."""
    normalized_id = str(body_id or "").strip().lower()
    if not normalized_id:
        raise ValueError("body_id is required")

    supported_bodies = {
        "sun",
        "moon",
        *_PLANET_ELEMENTS.keys(),
        *_JUPITER_MOONS.keys(),
        *_SATURN_MOONS.keys(),
    }
    if normalized_id not in supported_bodies:
        raise ValueError(f"Unsupported body_id '{normalized_id}'")

    return _body_position_au(normalized_id, _days_since_j2000(epoch))
