# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Static spacecraft index helpers for friendly search/autocomplete."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_INDEX_CACHE: List[Dict[str, Any]] | None = None
_INDEX_PATH = Path(__file__).with_name("spacecraftindex.json")


def get_spacecraft_index() -> List[Dict[str, Any]]:
    """Load and cache static spacecraft index entries."""
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE

    with _INDEX_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError("Invalid spacecraft index payload format")

    normalized = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command") or "").strip()
        name = str(item.get("display_name") or "").strip()
        if not command or not name:
            continue

        aliases = item.get("aliases") or []
        if not isinstance(aliases, list):
            aliases = []

        normalized.append(
            {
                "id": str(item.get("id") or command).strip(),
                "display_name": name,
                "command": command,
                "aliases": [str(alias).strip() for alias in aliases if str(alias).strip()],
                "agency": str(item.get("agency") or "").strip(),
                "mission_status": str(item.get("mission_status") or "unknown").strip().lower(),
                "status_label": str(item.get("status_label") or "").strip(),
                "status_notes": str(item.get("status_notes") or "").strip(),
                "status_source": str(item.get("status_source") or "").strip(),
            }
        )

    _INDEX_CACHE = normalized
    return normalized


def search_spacecraft_index(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search static spacecraft index by display name, command, and aliases."""
    entries = get_spacecraft_index()
    needle = (query or "").strip().lower()

    if not needle:
        return entries[: max(1, limit)]

    scored: List[tuple[int, Dict[str, Any]]] = []

    for entry in entries:
        name = entry["display_name"].lower()
        command = entry["command"].lower()
        aliases = [alias.lower() for alias in entry.get("aliases", [])]

        score = -1
        if needle == name or needle == command or needle in aliases:
            score = 100
        elif name.startswith(needle) or command.startswith(needle):
            score = 75
        elif any(alias.startswith(needle) for alias in aliases):
            score = 60
        elif needle in name or needle in command:
            score = 40
        elif any(needle in alias for alias in aliases):
            score = 30

        if score >= 0:
            scored.append((score, entry))

    scored.sort(key=lambda row: (-row[0], row[1]["display_name"]))
    return [entry for _, entry in scored[: max(1, limit)]]
