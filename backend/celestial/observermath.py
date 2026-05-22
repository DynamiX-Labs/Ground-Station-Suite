# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Local observer-centric sky-position math for celestial vectors."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, List

J2000_JD = 2451545.0
EARTH_OBLIQUITY_DEG = 23.439291


def _normalize_degrees(value: float) -> float:
    return value % 360.0


def _normalize_signed_degrees(value: float) -> float:
    wrapped = value % 360.0
    if wrapped > 180.0:
        wrapped -= 360.0
    return wrapped


def _julian_date(epoch: datetime) -> float:
    utc_epoch = epoch.astimezone(timezone.utc)
    year = utc_epoch.year
    month = utc_epoch.month
    day = utc_epoch.day

    frac_day = (
        utc_epoch.hour / 24.0
        + utc_epoch.minute / 1440.0
        + (utc_epoch.second + utc_epoch.microsecond / 1_000_000.0) / 86400.0
    )

    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + (a // 4)
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + frac_day
        + b
        - 1524.5
    )


def _gmst_deg(epoch: datetime) -> float:
    jd = _julian_date(epoch)
    t = (jd - J2000_JD) / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (jd - J2000_JD)
        + 0.000387933 * (t * t)
        - (t * t * t) / 38710000.0
    )
    return _normalize_degrees(gmst)


def _ecliptic_to_equatorial(x: float, y: float, z: float) -> List[float]:
    eps = math.radians(EARTH_OBLIQUITY_DEG)
    cos_eps = math.cos(eps)
    sin_eps = math.sin(eps)
    x_eq = x
    y_eq = y * cos_eps - z * sin_eps
    z_eq = y * sin_eps + z * cos_eps
    return [x_eq, y_eq, z_eq]


def compute_observer_sky_position(
    target_heliocentric_xyz_au: List[float],
    earth_heliocentric_xyz_au: List[float],
    epoch: datetime,
    observer_lat_deg: float,
    observer_lon_deg: float,
) -> Dict[str, object]:
    """Compute az/el from heliocentric vectors using local math."""
    if len(target_heliocentric_xyz_au) < 3 or len(earth_heliocentric_xyz_au) < 3:
        raise ValueError("Expected 3D target and earth vectors")

    tx, ty, tz = [float(v) for v in target_heliocentric_xyz_au[:3]]
    ex, ey, ez = [float(v) for v in earth_heliocentric_xyz_au[:3]]

    # Convert to geocentric vector in ecliptic frame.
    gx, gy, gz = tx - ex, ty - ey, tz - ez
    radius = math.sqrt(gx * gx + gy * gy + gz * gz)
    if radius <= 0.0:
        raise ValueError("Degenerate geocentric vector")

    x_eq, y_eq, z_eq = _ecliptic_to_equatorial(gx, gy, gz)
    eq_radius = math.sqrt(x_eq * x_eq + y_eq * y_eq + z_eq * z_eq)
    if eq_radius <= 0.0:
        raise ValueError("Degenerate equatorial vector")

    ra_deg = _normalize_degrees(math.degrees(math.atan2(y_eq, x_eq)))
    dec_rad = math.asin(max(-1.0, min(1.0, z_eq / eq_radius)))
    dec_deg = math.degrees(dec_rad)

    lst_deg = _normalize_degrees(_gmst_deg(epoch) + float(observer_lon_deg))
    ha_deg = _normalize_signed_degrees(lst_deg - ra_deg)

    lat_rad = math.radians(float(observer_lat_deg))
    ha_rad = math.radians(ha_deg)

    sin_el = math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(
        lat_rad
    ) * math.cos(ha_rad)
    sin_el = max(-1.0, min(1.0, sin_el))
    el_rad = math.asin(sin_el)
    el_deg = math.degrees(el_rad)

    y_az = -math.sin(ha_rad)
    x_az = math.tan(dec_rad) * math.cos(lat_rad) - math.sin(lat_rad) * math.cos(ha_rad)
    az_deg = _normalize_degrees(math.degrees(math.atan2(y_az, x_az)))

    return {
        "sky_position": {
            "az_deg": az_deg,
            "el_deg": el_deg,
            "ra_deg": ra_deg,
            "dec_deg": dec_deg,
        },
        "visibility": {
            "above_horizon": el_deg > 0.0,
            "visible": el_deg > 0.0,
            "horizon_threshold_deg": 0.0,
        },
    }
