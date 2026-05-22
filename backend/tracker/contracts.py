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

"""Tracker v2 contracts for multi-rotator / multi-tracker architecture.

This module defines canonical contract helpers used by handlers and services.
Runtime behavior remains backward compatible during migration, but all new
contracts are tracker-instance scoped.
"""

from __future__ import annotations

from typing import Any, TypedDict

TRACKING_STATE_NAME_PREFIX = "satellite-tracking"


class InvalidTrackerIdError(ValueError):
    """Raised when a tracker_id is missing or invalid."""


class TrackerCommandRequest(TypedDict, total=False):
    """Client request payload for tracker commands."""

    tracker_id: str
    value: dict[str, Any]


class TrackerEventEnvelope(TypedDict, total=False):
    """Server event envelope for tracker updates."""

    tracker_id: str
    tracking_state: dict[str, Any]
    satellite_data: dict[str, Any]
    rotator_data: dict[str, Any]
    rig_data: dict[str, Any]
    events: list[dict[str, Any]]


def normalize_tracker_id(candidate: Any) -> str:
    """Return a canonical tracker id, or empty string when not provided."""
    if candidate is None:
        return ""
    tracker_id = str(candidate).strip()
    if not tracker_id or tracker_id.lower() == "none":
        return ""
    return tracker_id


def require_tracker_id(candidate: Any) -> str:
    """Require a non-empty tracker_id and return it normalized."""
    tracker_id = normalize_tracker_id(candidate)
    if not tracker_id:
        raise InvalidTrackerIdError("tracker_id is required")
    return tracker_id


def get_tracking_state_name(tracker_id: str) -> str:
    """Get instance-specific tracking_state.name value for storage."""
    normalized = require_tracker_id(tracker_id)
    return f"{TRACKING_STATE_NAME_PREFIX}:{normalized}"
