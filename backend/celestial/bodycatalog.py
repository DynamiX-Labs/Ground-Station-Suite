# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Static solar-system body catalog for selectable celestial targets."""

from __future__ import annotations

from typing import Dict, List, Optional

_BODY_CATALOG: List[Dict[str, object]] = [
    {
        "body_id": "sun",
        "name": "Sun",
        "body_type": "star",
        "parent_body_id": None,
        "sort_order": 0,
    },
    {
        "body_id": "mercury",
        "name": "Mercury",
        "body_type": "planet",
        "parent_body_id": None,
        "sort_order": 10,
    },
    {
        "body_id": "venus",
        "name": "Venus",
        "body_type": "planet",
        "parent_body_id": None,
        "sort_order": 20,
    },
    {
        "body_id": "earth",
        "name": "Earth",
        "body_type": "planet",
        "parent_body_id": None,
        "sort_order": 30,
    },
    {
        "body_id": "moon",
        "name": "Moon",
        "body_type": "moon",
        "parent_body_id": "earth",
        "sort_order": 31,
    },
    {
        "body_id": "mars",
        "name": "Mars",
        "body_type": "planet",
        "parent_body_id": None,
        "sort_order": 40,
    },
    {
        "body_id": "jupiter",
        "name": "Jupiter",
        "body_type": "planet",
        "parent_body_id": None,
        "sort_order": 50,
    },
    {
        "body_id": "io",
        "name": "Io",
        "body_type": "moon",
        "parent_body_id": "jupiter",
        "sort_order": 51,
    },
    {
        "body_id": "europa",
        "name": "Europa",
        "body_type": "moon",
        "parent_body_id": "jupiter",
        "sort_order": 52,
    },
    {
        "body_id": "ganymede",
        "name": "Ganymede",
        "body_type": "moon",
        "parent_body_id": "jupiter",
        "sort_order": 53,
    },
    {
        "body_id": "callisto",
        "name": "Callisto",
        "body_type": "moon",
        "parent_body_id": "jupiter",
        "sort_order": 54,
    },
    {
        "body_id": "saturn",
        "name": "Saturn",
        "body_type": "planet",
        "parent_body_id": None,
        "sort_order": 60,
    },
    {
        "body_id": "enceladus",
        "name": "Enceladus",
        "body_type": "moon",
        "parent_body_id": "saturn",
        "sort_order": 61,
    },
    {
        "body_id": "rhea",
        "name": "Rhea",
        "body_type": "moon",
        "parent_body_id": "saturn",
        "sort_order": 62,
    },
    {
        "body_id": "titan",
        "name": "Titan",
        "body_type": "moon",
        "parent_body_id": "saturn",
        "sort_order": 63,
    },
    {
        "body_id": "iapetus",
        "name": "Iapetus",
        "body_type": "moon",
        "parent_body_id": "saturn",
        "sort_order": 64,
    },
    {
        "body_id": "uranus",
        "name": "Uranus",
        "body_type": "planet",
        "parent_body_id": None,
        "sort_order": 70,
    },
    {
        "body_id": "neptune",
        "name": "Neptune",
        "body_type": "planet",
        "parent_body_id": None,
        "sort_order": 80,
    },
]

_BODY_BY_ID: Dict[str, Dict[str, object]] = {
    str(entry["body_id"]): entry for entry in _BODY_CATALOG
}


def list_celestial_bodies() -> List[Dict[str, object]]:
    """Return static body catalog sorted by display order."""

    def sort_key(item: Dict[str, object]) -> int:
        value = item.get("sort_order")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 9999

    return [dict(entry) for entry in sorted(_BODY_CATALOG, key=sort_key)]


def get_celestial_body(body_id: str) -> Optional[Dict[str, object]]:
    """Get one catalog body by ID."""
    key = str(body_id or "").strip().lower()
    if not key:
        return None
    entry = _BODY_BY_ID.get(key)
    return dict(entry) if entry else None


def search_celestial_bodies(query: str, limit: int = 20) -> List[Dict[str, object]]:
    """Search body catalog by display name and body identifiers."""
    entries = list_celestial_bodies()
    needle = (query or "").strip().lower()

    if not needle:
        return entries[: max(1, limit)]

    scored: List[tuple[int, Dict[str, object]]] = []

    for entry in entries:
        body_id = str(entry.get("body_id") or "").strip().lower()
        name = str(entry.get("name") or "").strip().lower()
        body_type = str(entry.get("body_type") or "").strip().lower()
        parent_body_id = str(entry.get("parent_body_id") or "").strip().lower()

        score = -1
        if needle == body_id or needle == name:
            score = 100
        elif body_id.startswith(needle) or name.startswith(needle):
            score = 75
        elif needle in body_id or needle in name:
            score = 45
        elif needle == body_type or needle == parent_body_id:
            score = 30
        elif needle in body_type or needle in parent_body_id:
            score = 15

        if score >= 0:
            scored.append((score, entry))

    scored.sort(key=lambda row: (-row[0], str(row[1].get("name") or row[1].get("body_id") or "")))
    return [dict(entry) for _, entry in scored[: max(1, limit)]]
