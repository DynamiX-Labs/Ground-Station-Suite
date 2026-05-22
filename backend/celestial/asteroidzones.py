# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Static asteroid zone definitions for solar-system rendering.

Values are intentionally static for deterministic rendering and offline use.
Primary class boundaries are sourced from JPL SBDB filter documentation.

Sources:
- https://ssd-api.jpl.nasa.gov/doc/sbdb_filter.html
- https://ssd.jpl.nasa.gov/diagrams/mb_hist.html
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

ASTEROID_ZONES: List[Dict[str, Any]] = [
    {
        "id": "imb",
        "name": "Inner Main Belt",
        "class_code": "IMB",
        "a_min_au": 2.0,
        "a_max_au": 2.5,
        "color_hex": "#4F8CFF",
        "description": "JPL IMB-aligned belt slice (bounded by 3:1 resonance split for visualization).",
    },
    {
        "id": "mmb",
        "name": "Middle Main Belt",
        "class_code": "MBA",
        "a_min_au": 2.5,
        "a_max_au": 2.82,
        "color_hex": "#4FC3A1",
        "description": "JPL MBA interior section (between 3:1 and 5:2 resonance markers).",
    },
    {
        "id": "omb",
        "name": "Outer Main Belt",
        "class_code": "OMB",
        "a_min_au": 2.82,
        "a_max_au": 4.6,
        "color_hex": "#E0A458",
        "description": "JPL OMB-aligned outer section.",
    },
    {
        "id": "tjn",
        "name": "Jupiter Trojan Region",
        "class_code": "TJN",
        "a_min_au": 4.6,
        "a_max_au": 5.5,
        "color_hex": "#D97AA8",
        "description": "JPL Jupiter Trojan class semimajor-axis interval.",
    },
    {
        "id": "kuiper",
        "name": "Kuiper Belt",
        "class_code": "TNO",
        "a_min_au": 30.0,
        "a_max_au": 50.0,
        "color_hex": "#5EC8E5",
        "description": "Trans-Neptunian belt (classical and resonant populations, static display band).",
    },
    {
        "id": "scattered",
        "name": "Scattered Disk",
        "class_code": "TNO",
        "a_min_au": 50.0,
        "a_max_au": 100.0,
        "color_hex": "#8BA6FF",
        "description": "Outer trans-Neptunian scattered population display band.",
    },
]


ASTEROID_RESONANCE_GAPS: List[Dict[str, Any]] = [
    {"id": "3-1", "name": "3:1", "a_au": 2.50},
    {"id": "5-2", "name": "5:2", "a_au": 2.82},
    {"id": "7-3", "name": "7:3", "a_au": 2.96},
    {"id": "2-1", "name": "2:1", "a_au": 3.27},
]


def get_static_asteroid_zones() -> (
    Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]
):
    """Return static zone/gap payload and metadata for scene responses."""
    return (
        [dict(item) for item in ASTEROID_ZONES],
        [dict(item) for item in ASTEROID_RESONANCE_GAPS],
        {
            "source": "JPL-static",
            "references": [
                "https://ssd-api.jpl.nasa.gov/doc/sbdb_filter.html",
                "https://ssd.jpl.nasa.gov/diagrams/mb_hist.html",
            ],
        },
    )
