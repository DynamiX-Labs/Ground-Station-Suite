"""Orbital source CRUD wrappers.

This module provides domain-accurate function names while keeping
backward compatibility with legacy TLE-source CRUD implementation.
"""

from __future__ import annotations

from typing import List, Optional, Union
from uuid import UUID

from .tlesources import add_satellite_tle_source as _add_satellite_tle_source
from .tlesources import delete_satellite_tle_sources as _delete_satellite_tle_sources
from .tlesources import edit_satellite_tle_source as _edit_satellite_tle_source
from .tlesources import fetch_satellite_tle_source as _fetch_satellite_tle_source


async def fetch_orbital_source(
    session, orbital_source_id: Optional[Union[UUID, str]] = None
) -> dict:
    return await _fetch_satellite_tle_source(session, orbital_source_id)


async def add_orbital_source(session, payload: dict) -> dict:
    return await _add_satellite_tle_source(session, payload)


async def edit_orbital_source(session, orbital_source_id: str, payload: dict) -> dict:
    return await _edit_satellite_tle_source(session, orbital_source_id, payload)


async def delete_orbital_sources(session, orbital_source_ids: Union[List[str], dict]) -> dict:
    return await _delete_satellite_tle_sources(session, orbital_source_ids)


# Compatibility aliases for callers that still use TLE naming.
fetch_satellite_tle_source = _fetch_satellite_tle_source
add_satellite_tle_source = _add_satellite_tle_source
edit_satellite_tle_source = _edit_satellite_tle_source
delete_satellite_tle_sources = _delete_satellite_tle_sources
