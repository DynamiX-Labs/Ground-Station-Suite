# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Horizons API client for celestial vectors."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
logger = logging.getLogger("ground-station")


def _extract_ephemeris_lines(result_text: str) -> List[str]:
    lines = result_text.splitlines()
    in_data = False
    data_lines: List[str] = []

    for line in lines:
        if "$$SOE" in line:
            in_data = True
            continue
        if "$$EOE" in line:
            break
        if in_data and line.strip():
            data_lines.append(line.strip())
    return data_lines


def _parse_horizons_datetime(raw_value: str) -> Optional[datetime]:
    text = raw_value.strip()
    if not text:
        return None

    formats = (
        "A.D. %Y-%b-%d %H:%M:%S.%f",
        "A.D. %Y-%b-%d %H:%M:%S",
        "A.D. %Y-%b-%d %H:%M",
    )

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_horizons_observer_datetime(raw_value: str) -> Optional[datetime]:
    text = raw_value.strip()
    if not text:
        return None

    formats = (
        "%Y-%b-%d %H:%M:%S",
        "%Y-%b-%d %H:%M",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_vector_line(line: str) -> Optional[Dict[str, object]]:
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 8:
        return None

    try:
        x_val = float(parts[2])
        y_val = float(parts[3])
        z_val = float(parts[4])
        vx_val = float(parts[5])
        vy_val = float(parts[6])
        vz_val = float(parts[7])
    except (ValueError, IndexError):
        return None

    return {
        "epoch_utc": _parse_horizons_datetime(parts[1]),
        "position_xyz_au": [x_val, y_val, z_val],
        "velocity_xyz_au_per_day": [vx_val, vy_val, vz_val],
    }


def _parse_observer_line(line: str) -> Optional[Dict[str, object]]:
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 9:
        return None

    epoch = _parse_horizons_observer_datetime(parts[0])
    if not epoch:
        return None

    try:
        az_deg = float(parts[7])
        el_deg = float(parts[8])
    except (ValueError, IndexError):
        return None

    sky_position: Dict[str, object] = {
        "az_deg": az_deg,
        "el_deg": el_deg,
    }

    # If available from requested quantities, include apparent RA/DEC strings.
    if len(parts) > 6 and parts[5] and parts[6]:
        sky_position["ra_apparent"] = parts[5]
        sky_position["dec_apparent"] = parts[6]

    return {
        "epoch_utc": epoch,
        "sky_position": sky_position,
    }


def fetch_celestial_vectors(
    command: str,
    epoch: datetime,
    past_hours: int = 36,
    future_hours: int = 36,
    step_minutes: int = 120,
    timeout_seconds: float = 10.0,
) -> Dict[str, object]:
    """Fetch celestial state vectors from Horizons at a given epoch."""
    utc_epoch = epoch.astimezone(timezone.utc)
    bounded_past_hours = max(1, int(past_hours))
    bounded_future_hours = max(1, int(future_hours))
    bounded_step_minutes = max(5, int(step_minutes))
    start_time = (utc_epoch - timedelta(hours=bounded_past_hours)).strftime("%Y-%m-%d %H:%M")
    stop_time = (utc_epoch + timedelta(hours=bounded_future_hours)).strftime("%Y-%m-%d %H:%M")

    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER": "'500@10'",
        "REF_PLANE": "ECLIPTIC",
        "OUT_UNITS": "AU-D",
        "VEC_TABLE": "2",
        "CSV_FORMAT": "YES",
        "START_TIME": f"'{start_time}'",
        "STOP_TIME": f"'{stop_time}'",
        "STEP_SIZE": f"'{bounded_step_minutes} m'",
    }

    # Measure the remote Horizons HTTP round-trip for vectors retrieval.
    request_started_at = time.perf_counter()
    try:
        response = requests.get(HORIZONS_API_URL, params=params, timeout=timeout_seconds)
        response.raise_for_status()
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - request_started_at) * 1000.0
        logger.warning(
            "Horizons vectors request failed for command '%s' in %.1f ms "
            "(window=%s..%s step=%sm): %s",
            command,
            elapsed_ms,
            start_time,
            stop_time,
            bounded_step_minutes,
            exc,
        )
        raise

    elapsed_ms = (time.perf_counter() - request_started_at) * 1000.0
    logger.info(
        "Horizons vectors request completed for command '%s' in %.1f ms "
        "(status=%s window=%s..%s step=%sm)",
        command,
        elapsed_ms,
        response.status_code,
        start_time,
        stop_time,
        bounded_step_minutes,
    )

    payload = response.json()
    result_text = payload.get("result", "")
    data_lines = _extract_ephemeris_lines(result_text)

    if not data_lines:
        raise ValueError(f"No ephemeris data returned by Horizons for command '{command}'")

    parsed_rows = [row for row in (_parse_vector_line(line) for line in data_lines) if row]
    if not parsed_rows:
        raise ValueError(f"Failed parsing Horizons vector line for command '{command}'")

    # Use the closest parsed epoch to represent "current" state.
    chosen_row = parsed_rows[0]
    chosen_dt = chosen_row.get("epoch_utc")
    chosen_delta = (
        abs((chosen_dt - utc_epoch).total_seconds())
        if isinstance(chosen_dt, datetime)
        else float("inf")
    )
    for row in parsed_rows[1:]:
        row_dt = row.get("epoch_utc")
        if not isinstance(row_dt, datetime):
            continue
        row_delta = abs((row_dt - utc_epoch).total_seconds())
        if row_delta < chosen_delta:
            chosen_row = row
            chosen_delta = row_delta

    trajectory_points: List[List[float]] = []
    trajectory_times_utc: List[str] = []
    for row in parsed_rows:
        position = row.get("position_xyz_au")
        if isinstance(position, list) and len(position) >= 3:
            trajectory_points.append([float(position[0]), float(position[1]), float(position[2])])
            row_epoch = row.get("epoch_utc")
            if isinstance(row_epoch, datetime):
                trajectory_times_utc.append(row_epoch.astimezone(timezone.utc).isoformat())
            else:
                trajectory_times_utc.append("")

    signature = payload.get("signature", {})

    return {
        "command": command,
        "position_xyz_au": chosen_row["position_xyz_au"],
        "velocity_xyz_au_per_day": chosen_row["velocity_xyz_au_per_day"],
        "orbit_samples_xyz_au": trajectory_points,
        "orbit_sample_times_utc": trajectory_times_utc,
        "orbit_sampling": {
            "past_hours": bounded_past_hours,
            "future_hours": bounded_future_hours,
            "step_minutes": bounded_step_minutes,
        },
        "source": "horizons",
        "horizons_signature": signature,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def fetch_celestial_observer_state(
    command: str,
    epoch: datetime,
    observer_lat_deg: float,
    observer_lon_deg: float,
    observer_alt_km: float = 0.0,
    timeout_seconds: float = 10.0,
) -> Dict[str, object]:
    """Fetch observer-centric sky position (az/el) from Horizons for a target."""
    utc_epoch = epoch.astimezone(timezone.utc)
    start_time = (utc_epoch - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    stop_time = (utc_epoch + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")

    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{observer_lon_deg:.8f},{observer_lat_deg:.8f},{observer_alt_km:.6f}'",
        "START_TIME": f"'{start_time}'",
        "STOP_TIME": f"'{stop_time}'",
        "STEP_SIZE": "'5 m'",
        "QUANTITIES": "'1,2,4,20,23,24'",
        "CSV_FORMAT": "YES",
    }

    response = requests.get(HORIZONS_API_URL, params=params, timeout=timeout_seconds)
    response.raise_for_status()

    payload = response.json()
    result_text = payload.get("result", "")
    data_lines = _extract_ephemeris_lines(result_text)

    if not data_lines:
        raise ValueError(f"No observer ephemeris data returned by Horizons for command '{command}'")

    parsed_rows = [row for row in (_parse_observer_line(line) for line in data_lines) if row]
    if not parsed_rows:
        raise ValueError(f"Failed parsing Horizons observer line for command '{command}'")

    chosen_row = parsed_rows[0]
    chosen_dt = chosen_row.get("epoch_utc")
    chosen_delta = (
        abs((chosen_dt - utc_epoch).total_seconds())
        if isinstance(chosen_dt, datetime)
        else float("inf")
    )
    for row in parsed_rows[1:]:
        row_dt = row.get("epoch_utc")
        if not isinstance(row_dt, datetime):
            continue
        row_delta = abs((row_dt - utc_epoch).total_seconds())
        if row_delta < chosen_delta:
            chosen_row = row
            chosen_delta = row_delta

    sky_position = chosen_row.get("sky_position")
    if not isinstance(sky_position, dict):
        raise ValueError(f"Missing sky position data for command '{command}'")

    el_deg = float(sky_position.get("el_deg", 0.0))

    return {
        "command": command,
        "sky_position": sky_position,
        "visibility": {
            "above_horizon": el_deg > 0.0,
            "visible": el_deg > 0.0,
            "horizon_threshold_deg": 0.0,
        },
        "source": "horizons-observer",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
    }
