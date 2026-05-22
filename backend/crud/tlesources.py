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

import json
import random
import re
import string
import traceback
import uuid
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.common import logger, serialize_object
from common.utils import convert_strings_to_uuids
from db.models import Groups, OrbitalSources, SatelliteOrbits, Satellites, Transmitters

SUPPORTED_CENTRAL_BODIES = {"earth", "moon", "mars"}
SUPPORTED_AUTH_TYPES = {"none", "basic", "token"}
SUPPORTED_QUERY_MODES = {"url"}
LEGACY_PROVIDER_ALIASES = {"celestrak": "generic_http"}
SPACE_TRACK_GP_BASE_URL = "https://www.space-track.org/basicspacedata/query/class/gp"


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"Invalid boolean value: {value}")


def _coerce_optional_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    text = str(value).strip()
    if not text:
        return None
    return uuid.UUID(text)


def _infer_provider(url: Optional[str]) -> str:
    lowered = (url or "").lower()
    if "space-track" in lowered:
        return "space_track"
    return "generic_http"


def _normalize_provider(provider: Optional[str], url: Optional[str]) -> str:
    normalized = (_clean_optional_text(provider) or _infer_provider(url)).lower()
    return LEGACY_PROVIDER_ALIASES.get(normalized, normalized)


def _infer_adapter(provider: str, source_format: str) -> str:
    if provider == "space_track":
        return "space_track_gp"
    if source_format == "omm":
        return "http_omm"
    return "http_3le"


def _normalize_norad_ids(value: Any) -> List[int]:
    candidate = value
    if isinstance(candidate, str):
        cleaned = candidate.strip()
        if not cleaned:
            return []
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, str):
                candidate = re.split(r"[\s,]+", parsed.strip())
            else:
                candidate = parsed
        except json.JSONDecodeError:
            candidate = re.split(r"[\s,]+", cleaned)
    elif candidate is None:
        return []
    elif isinstance(candidate, (int, float)):
        candidate = [candidate]

    if not isinstance(candidate, (list, tuple, set)):
        return []

    normalized: List[int] = []
    seen: set[int] = set()
    for item in candidate:
        try:
            norad_id = int(item)
        except (TypeError, ValueError):
            continue
        if norad_id <= 0 or norad_id in seen:
            continue
        normalized.append(norad_id)
        seen.add(norad_id)
    return normalized


def _normalize_source_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    normalized["name"] = _clean_optional_text(normalized.get("name"))
    normalized["url"] = _clean_optional_text(normalized.get("url"))

    source_format = _clean_optional_text(normalized.get("format")) or "3le"
    normalized["format"] = source_format.lower()

    normalized["provider"] = _normalize_provider(normalized.get("provider"), normalized["url"])
    query_mode = (_clean_optional_text(normalized.get("query_mode")) or "url").lower()
    if query_mode == "group_norad":
        query_mode = "url"
    if query_mode not in SUPPORTED_QUERY_MODES:
        raise ValueError(
            f"Invalid query_mode '{query_mode}'. Expected one of: {sorted(SUPPORTED_QUERY_MODES)}"
        )
    normalized["query_mode"] = query_mode
    normalized["group_id"] = _coerce_optional_uuid(normalized.get("group_id"))
    normalized["norad_ids"] = _normalize_norad_ids(normalized.get("norad_ids"))

    adapter = _clean_optional_text(normalized.get("adapter")) or _infer_adapter(
        normalized["provider"], normalized["format"]
    )
    normalized["adapter"] = adapter.lower()

    if "enabled" in normalized:
        normalized["enabled"] = _coerce_bool(normalized.get("enabled"))
    else:
        normalized["enabled"] = True

    if "priority" in normalized and normalized.get("priority") is not None:
        normalized["priority"] = int(normalized["priority"])
    else:
        normalized["priority"] = 100

    central_body = (_clean_optional_text(normalized.get("central_body")) or "earth").lower()
    if central_body not in SUPPORTED_CENTRAL_BODIES:
        raise ValueError(
            f"Invalid central_body '{central_body}'. Expected one of: {sorted(SUPPORTED_CENTRAL_BODIES)}"
        )
    normalized["central_body"] = central_body

    auth_type = (_clean_optional_text(normalized.get("auth_type")) or "none").lower()
    if auth_type not in SUPPORTED_AUTH_TYPES:
        raise ValueError(
            f"Invalid auth_type '{auth_type}'. Expected one of: {sorted(SUPPORTED_AUTH_TYPES)}"
        )
    normalized["auth_type"] = auth_type

    normalized["username"] = _clean_optional_text(normalized.get("username"))
    normalized["password"] = _clean_optional_text(normalized.get("password"))

    raw_config = normalized.get("config")
    if raw_config is None:
        normalized["config"] = None
    elif isinstance(raw_config, (dict, list)):
        normalized["config"] = raw_config
    elif isinstance(raw_config, str):
        raw_config = raw_config.strip()
        if not raw_config:
            normalized["config"] = None
        else:
            parsed = json.loads(raw_config)
            if not isinstance(parsed, (dict, list)):
                raise ValueError("config must be a JSON object or JSON array")
            normalized["config"] = parsed
    else:
        raise ValueError("config must be a dict, list, JSON string, or null")

    if not normalized["name"]:
        raise ValueError("Missing required field: name")
    if normalized["provider"] == "space_track":
        normalized["url"] = normalized["url"] or SPACE_TRACK_GP_BASE_URL
    if not normalized["url"]:
        raise ValueError("Missing required field: url")

    if normalized["provider"] == "space_track":
        normalized["query_mode"] = "url"
        normalized["group_id"] = None
        normalized["adapter"] = "space_track_gp"
        if not normalized["norad_ids"]:
            raise ValueError("space_track sources require at least one NORAD ID in norad_ids")
        if auth_type != "basic":
            raise ValueError("space_track_gp adapter requires auth_type='basic'")
    else:
        normalized["norad_ids"] = None

    if auth_type == "none":
        normalized["username"] = None
        normalized["password"] = None
    elif auth_type == "basic":
        if not normalized["username"] or not normalized["password"]:
            raise ValueError("auth_type='basic' requires username and password")
    elif auth_type == "token":
        if not normalized["password"]:
            raise ValueError("auth_type='token' requires password field to hold the token value")

    allowed_fields = {column.name for column in OrbitalSources.__table__.columns}
    return {key: value for key, value in normalized.items() if key in allowed_fields}


async def fetch_satellite_tle_source(
    session: AsyncSession, satellite_tle_source_id: Optional[Union[uuid.UUID, str]] = None
) -> dict:
    """
    Retrieve satellite TLE source records.
    If an ID is provided, fetch the specific record; otherwise, return all sources.
    """
    try:
        if satellite_tle_source_id is None:
            result = await session.execute(select(OrbitalSources))
            sources = result.scalars().all()
            sources = json.loads(json.dumps(sources, default=serialize_object))
            sources = serialize_object(sources)
            return {"success": True, "data": sources}

        else:
            # Convert to UUID if it's a string
            if isinstance(satellite_tle_source_id, str):
                satellite_tle_source_id = uuid.UUID(satellite_tle_source_id)

            result = await session.execute(
                select(OrbitalSources).filter(OrbitalSources.id == satellite_tle_source_id)
            )
            source = result.scalars().first()
            if source:
                source = serialize_object(source)
                return {"success": True, "data": source}

            return {"success": False, "error": "Satellite TLE source not found"}

    except Exception as e:
        logger.error(f"Error fetching satellite TLE source: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def add_satellite_tle_source(session: AsyncSession, payload: dict) -> dict:
    """
    Create a new satellite TLE source record with the provided payload.
    """
    try:
        payload = dict(payload or {})

        # Generate random identifier string
        payload["identifier"] = "".join(random.choices(string.ascii_letters, k=16))

        payload.pop("added", None)
        payload.pop("updated", None)
        payload.pop("id", None)

        payload = _normalize_source_payload(payload)

        new_source = OrbitalSources(**payload)
        session.add(new_source)
        await session.commit()
        await session.refresh(new_source)
        new_source = serialize_object(new_source)
        return {"success": True, "data": new_source}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding satellite TLE source: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def edit_satellite_tle_source(
    session: AsyncSession, satellite_tle_source_id: str, payload: dict
) -> dict:
    """
    Update an existing satellite TLE source record with new values provided in payload.
    Returns a result object containing the updated record or an error message.
    """
    try:
        payload = dict(payload or {})
        payload.pop("added", None)
        payload.pop("updated", None)
        payload.pop("id", None)
        payload.pop("identifier", None)
        source_id = uuid.UUID(satellite_tle_source_id)

        result = await session.execute(
            select(OrbitalSources).filter(OrbitalSources.id == source_id)
        )
        source = result.scalars().first()
        if not source:
            return {"success": False, "error": "Satellite TLE source not found"}

        merged_payload = {
            column.name: getattr(source, column.name) for column in OrbitalSources.__table__.columns
        }
        merged_payload.update(payload)
        normalized_payload = _normalize_source_payload(merged_payload)

        for key, value in normalized_payload.items():
            if key in {"id", "identifier", "added", "updated"}:
                continue
            if hasattr(source, key):
                setattr(source, key, value)

        await session.commit()
        await session.refresh(source)
        source = serialize_object(source)
        return {"success": True, "data": source}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error editing satellite TLE source: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def delete_satellite_tle_sources(
    session: AsyncSession, satellite_tle_source_ids: Union[List[str], dict]
) -> dict:
    """
    Deletes multiple satellite TLE source records using their IDs.
    Before deleting each TLE source, it finds the corresponding satellite group,
    deletes all transmitters and satellites that came from this TLE source, then deletes the group.
    """
    try:
        assert isinstance(satellite_tle_source_ids, list), "TLE source list must be a list"

        satellite_tle_source_ids = convert_strings_to_uuids(satellite_tle_source_ids)

        # Fetch sources that match the provided IDs
        result = await session.execute(
            select(OrbitalSources).filter(OrbitalSources.id.in_(satellite_tle_source_ids))
        )
        sources = result.scalars().all()

        # Determine which IDs were found
        found_ids = [source.id for source in sources]
        not_found_ids = [sat_id for sat_id in satellite_tle_source_ids if sat_id not in found_ids]

        if not sources:
            return {"success": False, "error": "None of the Satellite TLE sources were found."}

        deletion_summary = []

        for source in sources:
            source_identifier = source.identifier
            source_name = source.name

            # Find the corresponding satellite group by identifier
            group_result = await session.execute(
                select(Groups).filter(Groups.identifier == source_identifier)
            )
            satellite_group = group_result.scalar_one_or_none()

            satellites_deleted = 0
            transmitters_deleted = 0
            group_deleted = False

            if satellite_group:
                # Get the list of satellite NORAD IDs from the group
                satellite_norad_ids = satellite_group.satellite_ids or []

                if satellite_norad_ids:
                    # First, delete all transmitters associated with these satellites
                    # to avoid foreign key constraint violations
                    transmitters_result = await session.execute(
                        select(Transmitters).filter(
                            Transmitters.norad_cat_id.in_(satellite_norad_ids)
                        )
                    )
                    transmitters_to_delete = transmitters_result.scalars().all()

                    for transmitter in transmitters_to_delete:
                        await session.delete(transmitter)
                        transmitters_deleted += 1

                    # Now delete all satellites that came from this TLE source
                    satellites_result = await session.execute(
                        select(Satellites).filter(Satellites.norad_id.in_(satellite_norad_ids))
                    )
                    satellites_to_delete = satellites_result.scalars().all()

                    for satellite in satellites_to_delete:
                        await session.delete(satellite)
                        satellites_deleted += 1

                # Delete the satellite group
                await session.delete(satellite_group)
                group_deleted = True

            # Finally, delete the TLE source record
            await session.execute(
                update(SatelliteOrbits)
                .where(SatelliteOrbits.source_id == source.id)
                .values(source_id=None)
            )
            await session.delete(source)

            deletion_summary.append(
                {
                    "source_id": str(source.id),
                    "source_name": source_name,
                    "source_identifier": source_identifier,
                    "transmitters_deleted": transmitters_deleted,
                    "satellites_deleted": satellites_deleted,
                    "group_deleted": group_deleted,
                }
            )

        # Commit the changes
        await session.commit()

        # Construct a success message
        total_transmitters_deleted = sum(item["transmitters_deleted"] for item in deletion_summary)
        total_satellites_deleted = sum(item["satellites_deleted"] for item in deletion_summary)
        total_groups_deleted = sum(1 for item in deletion_summary if item["group_deleted"])

        message = (
            f"Successfully deleted {len(found_ids)} TLE source(s), "
            f"{total_transmitters_deleted} transmitter(s), "
            f"{total_satellites_deleted} satellite(s), and "
            f"{total_groups_deleted} satellite group(s)."
        )

        if not_found_ids:
            message += f" The following TLE source IDs were not found: {not_found_ids}."

        return {"success": True, "data": message, "deletion_summary": deletion_summary}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting satellite TLE sources: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def fetch_orbital_source(
    session: AsyncSession, orbital_source_id: Optional[Union[uuid.UUID, str]] = None
) -> dict:
    """Domain-accurate alias for fetching orbital sources."""
    return await fetch_satellite_tle_source(session, orbital_source_id)


async def add_orbital_source(session: AsyncSession, payload: dict) -> dict:
    """Domain-accurate alias for creating orbital sources."""
    return await add_satellite_tle_source(session, payload)


async def edit_orbital_source(session: AsyncSession, orbital_source_id: str, payload: dict) -> dict:
    """Domain-accurate alias for updating orbital sources."""
    return await edit_satellite_tle_source(session, orbital_source_id, payload)


async def delete_orbital_sources(
    session: AsyncSession, orbital_source_ids: Union[List[str], dict]
) -> dict:
    """Domain-accurate alias for deleting orbital sources."""
    return await delete_satellite_tle_sources(session, orbital_source_ids)
