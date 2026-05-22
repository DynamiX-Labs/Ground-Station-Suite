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

"""Orbit source adapters for sync ingestion."""

from __future__ import annotations

import asyncio
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import unquote, urlparse

import requests
from sgp4 import omm
from sgp4.api import Satrec
from sgp4.exporter import export_tle

from tlesync.utils import parse_norad_id_from_line1, simple_parse_3le

DEFAULT_REQUEST_TIMEOUT_SECONDS = 20
SPACE_TRACK_LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
SPACE_TRACK_GP_QUERY_URL = "https://www.space-track.org/basicspacedata/query/class/gp"
DEFAULT_NORAD_BATCH_SIZE = 200


def fetch_source_orbit_records(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch and normalize orbit records from one configured source."""
    adapter = str(source.get("adapter") or "http_3le").strip().lower()
    if adapter == "http_3le":
        return _fetch_http_3le(source)
    if adapter == "http_omm":
        return _fetch_http_omm(source)
    if adapter == "space_track_gp":
        return _fetch_space_track_gp(source)
    raise ValueError(f"Unsupported orbit source adapter: {adapter}")


async def async_fetch_source_orbit_records(
    source: Dict[str, Any], executor
) -> List[Dict[str, Any]]:
    """Run source fetch in thread pool, like existing sync URL fetches."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, fetch_source_orbit_records, source)


def build_space_track_norad_source_batches(
    source: Dict[str, Any], norad_ids: Optional[Iterable[int]] = None
) -> List[Dict[str, Any]]:
    """Build concrete provider requests for a Space-Track NORAD ID source."""
    adapter = str(source.get("adapter") or "").strip().lower()
    provider = str(source.get("provider") or "").strip().lower()
    if adapter != "space_track_gp" or provider != "space_track":
        raise ValueError("NORAD ID batching is currently supported only for Space-Track GP sources")

    ids_input = source.get("norad_ids") if norad_ids is None else norad_ids
    ids = _normalize_norad_ids(ids_input)
    if not ids:
        raise ValueError("space_track sources require at least one NORAD ID in norad_ids")

    batch_size = _resolve_norad_batch_size()
    batches = []
    for start in range(0, len(ids), batch_size):
        batch_ids = ids[start : start + batch_size]
        batch_source = dict(source)
        batch_source["url"] = _build_space_track_norad_query_url(source, batch_ids)
        batch_source["source_object_ids"] = batch_ids
        batches.append(batch_source)
    return batches


# Backward-compatible alias for previous function name.
def build_group_norad_source_batches(
    source: Dict[str, Any], norad_ids: Iterable[int]
) -> List[Dict[str, Any]]:
    return build_space_track_norad_source_batches(source, norad_ids)


def _fetch_http_3le(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    response = requests.get(source["url"], timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return _normalize_tle_records(response.text, source=source)


def _fetch_http_omm(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    response = requests.get(source["url"], timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return _normalize_omm_records(response.text, source=source)


def _fetch_space_track_gp(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    if _is_unfiltered_space_track_gp_url(source.get("url")):
        raise ValueError(
            "Refusing to fetch unfiltered Space-Track GP source URL. "
            "Add Space-Track query predicates such as NORAD_CAT_ID."
        )

    auth_type = str(source.get("auth_type") or "none").strip().lower()
    if auth_type != "basic":
        raise ValueError("space_track_gp adapter requires auth_type='basic'")

    username = str(source.get("username") or "").strip()
    password = str(source.get("password") or "").strip()
    if not username or not password:
        raise ValueError("space_track_gp adapter requires username and password")

    with requests.Session() as session:
        login_response = session.post(
            SPACE_TRACK_LOGIN_URL,
            data={"identity": username, "password": password},
            timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        )
        login_response.raise_for_status()

        response = session.get(source["url"], timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()

    source_format = str(source.get("format") or "").strip().lower()
    if source_format in {"3le", "tle"}:
        return _normalize_tle_records(response.text, source=source)
    if source_format == "omm":
        return _normalize_omm_records(response.text, source=source)

    # Fallback when format is missing: try OMM first and then 3LE.
    try:
        return _normalize_omm_records(response.text, source=source)
    except Exception:
        return _normalize_tle_records(response.text, source=source)


def _normalize_norad_ids(norad_ids: Any) -> List[int]:
    if norad_ids is None:
        return []

    if isinstance(norad_ids, str):
        cleaned = norad_ids.strip()
        if not cleaned:
            return []
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, str):
                tokens = re.split(r"[\s,]+", parsed.strip())
                norad_ids = [token for token in tokens if token]
            else:
                norad_ids = parsed
        except json.JSONDecodeError:
            tokens = re.split(r"[\s,]+", cleaned)
            norad_ids = [token for token in tokens if token]

    if isinstance(norad_ids, (int, float)):
        norad_ids = [norad_ids]

    if not isinstance(norad_ids, (list, tuple, set)):
        return []

    normalized: List[int] = []
    seen = set()
    for item in norad_ids:
        try:
            norad_id = int(item)
        except (TypeError, ValueError):
            continue
        if norad_id <= 0 or norad_id in seen:
            continue
        normalized.append(norad_id)
        seen.add(norad_id)
    return normalized


def _resolve_norad_batch_size() -> int:
    # Keep Space-Track NORAD batching deterministic and bounded.
    return DEFAULT_NORAD_BATCH_SIZE


def _is_unfiltered_space_track_gp_url(url: Any) -> bool:
    text = _clean_optional_text(url)
    if not text or "{norad_ids}" in text:
        return False

    parsed = urlparse(text)
    path_parts = [
        unquote(part).strip() for part in parsed.path.strip("/").split("/") if unquote(part).strip()
    ]
    lowered_parts = [part.lower() for part in path_parts]

    try:
        class_index = lowered_parts.index("class")
    except ValueError:
        return False
    if class_index + 1 >= len(lowered_parts) or lowered_parts[class_index + 1] != "gp":
        return False

    trailing_parts = lowered_parts[class_index + 2 :]
    if not trailing_parts:
        return True

    directive_parts = {"format", "orderby", "limit", "emptyresult", "metadata", "distinct"}
    index = 0
    while index < len(trailing_parts):
        if trailing_parts[index] not in directive_parts:
            return False
        # These directives shape the response but do not filter the object set.
        index += 2 if index + 1 < len(trailing_parts) else 1
    return True


def _build_space_track_norad_query_url(source: Dict[str, Any], norad_ids: List[int]) -> str:
    ids_csv = ",".join(str(norad_id) for norad_id in norad_ids)
    source_format = str(source.get("format") or "omm").strip().lower()
    output_format = "tle" if source_format in {"3le", "tle"} else "json"
    configured_url = _clean_optional_text(source.get("url")) or SPACE_TRACK_GP_QUERY_URL

    # Advanced users can provide their own full Space-Track query template.
    if "{norad_ids}" in configured_url:
        return configured_url.replace("{norad_ids}", ids_csv).replace("{format}", output_format)

    return (
        f"{configured_url.rstrip('/')}"
        f"/NORAD_CAT_ID/{ids_csv}"
        f"/orderby/NORAD_CAT_ID"
        f"/format/{output_format}"
    )


def _normalize_tle_records(content: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
    satellites = simple_parse_3le(content)
    source_id = source.get("id")
    central_body = str(source.get("central_body") or "earth").strip().lower()
    normalized: List[Dict[str, Any]] = []
    for satellite in satellites:
        line1 = satellite["line1"].strip()
        line2 = satellite["line2"].strip()
        norad_id = parse_norad_id_from_line1(line1)
        normalized.append(
            {
                "name": satellite["name"].strip(),
                "norad_id": norad_id,
                "line1": line1,
                "line2": line2,
                "model_kind": "tle",
                "orbit_payload": None,
                "orbit_epoch": None,
                "source_id": source_id,
                "source_object_id": str(norad_id),
                "source_updated_at": None,
                "central_body": central_body,
            }
        )
    return normalized


def _normalize_omm_records(content: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
    omm_rows = _parse_omm_rows(content)
    source_id = source.get("id")
    central_body = str(source.get("central_body") or "earth").strip().lower()
    normalized: List[Dict[str, Any]] = []
    for row in omm_rows:
        fields = _normalize_omm_fields(row)
        satrec = Satrec()
        omm.initialize(satrec, fields)
        tle1, tle2 = export_tle(satrec)

        norad_id = int(fields["NORAD_CAT_ID"])
        epoch = _parse_epoch_datetime(fields.get("EPOCH"))
        name = (
            _clean_optional_text(fields.get("OBJECT_NAME"))
            or _clean_optional_text(fields.get("OBJECT_ID"))
            or f"NORAD {norad_id}"
        )

        normalized.append(
            {
                "name": name,
                "norad_id": norad_id,
                "line1": tle1.strip(),
                "line2": tle2.strip(),
                "model_kind": "omm",
                "orbit_payload": dict(row),
                "orbit_epoch": epoch,
                "source_id": source_id,
                "source_object_id": _clean_optional_text(fields.get("OBJECT_ID")) or str(norad_id),
                "source_updated_at": epoch,
                "central_body": central_body,
            }
        )
    return normalized


def _parse_omm_rows(content: str) -> List[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return []

    if text.startswith("{") or text.startswith("["):
        payload = json.loads(text)
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            if isinstance(payload.get("data"), list):
                rows = payload["data"]
            else:
                rows = [payload]
        else:
            raise ValueError("Unsupported OMM JSON payload")
        return [dict(row) for row in rows if isinstance(row, dict)]

    if text.startswith("<"):
        return [dict(row) for row in omm.parse_xml(io.StringIO(text))]

    return [dict(row) for row in omm.parse_csv(io.StringIO(text))]


def _normalize_omm_fields(raw_fields: Dict[str, Any]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in raw_fields.items():
        if key is None:
            continue
        clean_key = str(key).strip().upper()
        if not clean_key:
            continue
        if value is None:
            continue
        normalized[clean_key] = str(value).strip()

    if "EPOCH" not in normalized:
        raise ValueError("OMM row missing EPOCH")

    # sgp4.omm.initialize expects fixed epoch format without timezone suffix.
    normalized["EPOCH"] = _normalize_epoch_for_sgp4(normalized["EPOCH"])

    # Some providers omit these; default values keep initialization stable.
    normalized.setdefault("CLASSIFICATION_TYPE", "U")
    normalized.setdefault("EPHEMERIS_TYPE", "0")
    normalized.setdefault("ELEMENT_SET_NO", "0")
    normalized.setdefault("REV_AT_EPOCH", "0")
    normalized.setdefault("MEAN_MOTION_DOT", "0.0")
    normalized.setdefault("MEAN_MOTION_DDOT", "0.0")
    normalized.setdefault("BSTAR", "0.0")

    required = {
        "OBJECT_ID",
        "NORAD_CAT_ID",
        "EPOCH",
        "INCLINATION",
        "RA_OF_ASC_NODE",
        "ECCENTRICITY",
        "ARG_OF_PERICENTER",
        "MEAN_ANOMALY",
        "MEAN_MOTION",
    }
    missing = sorted(field for field in required if field not in normalized)
    if missing:
        raise ValueError(f"OMM row missing required fields: {missing}")

    return normalized


def _normalize_epoch_for_sgp4(epoch_value: str) -> str:
    dt = _parse_epoch_datetime(epoch_value)
    if dt is None:
        raise ValueError(f"Invalid OMM epoch value: {epoch_value}")
    return dt.astimezone(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S.%f")


def _parse_epoch_datetime(value: Optional[str]) -> Optional[datetime]:
    cleaned = _clean_optional_text(value)
    if not cleaned:
        return None

    normalized = cleaned.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None
