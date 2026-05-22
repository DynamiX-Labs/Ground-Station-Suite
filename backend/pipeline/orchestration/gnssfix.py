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

from typing import Any, Dict, Optional, Tuple

import numpy as np


def _to_finite_float(value: Any) -> Optional[float]:
    """Convert to float and reject NaN/inf so fix checks stay deterministic."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if np.isfinite(parsed) else None


def derive_gnss_fix_status_from_output(output: Dict[str, Any]) -> Optional[str]:
    """
    Determine GNSS fix status from decoder output using GNSS evidence fields.

    Returns:
        - "FIX" or "NO FIX" when output includes GNSS fix/no-fix signal evidence
        - None when output is unrelated to fix state
    """
    if not isinstance(output, dict):
        return None

    # Allow decoder-side/pre-enriched explicit status to override heuristic parsing.
    explicit = str(output.get("gnss_fix_status") or "").strip().upper()
    if explicit in {"FIX", "NO FIX"}:
        return explicit

    event_type = str(output.get("event") or "").strip().lower()
    # GNSS activity heartbeat is transport telemetry; it should not drive fix transitions.
    if event_type == "gnss_activity":
        return None

    latitude = _to_finite_float(output.get("latitude"))
    longitude = _to_finite_float(output.get("longitude"))
    has_coords = latitude is not None and longitude is not None

    has_pvt_field = output.get("has_pvt") is not None
    has_pvt = bool(output.get("has_pvt")) if has_pvt_field else False

    fix_quality_raw = output.get("fix_quality")
    has_fix_quality_field = fix_quality_raw is not None and str(fix_quality_raw).strip() != ""
    has_fix_quality = has_fix_quality_field and str(fix_quality_raw).strip() != "0"

    is_nmea = event_type in {"nmea", "nmea_gga", "nmea_rmc"}
    has_fix_signal = has_coords or has_fix_quality_field or has_pvt_field or is_nmea
    if not has_fix_signal:
        return None

    return "FIX" if (has_coords or has_fix_quality or has_pvt) else "NO FIX"


def gnss_fix_stream_key(data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Build a stable per-decoder stream key for GNSS fix transition tracking.

    We intentionally use session+vfo because decoder-output messages do not always
    include decoder_id.
    """
    session_id = str(data.get("session_id") or "")
    vfo = data.get("vfo")
    return session_id, str(vfo if vfo is not None else "")
