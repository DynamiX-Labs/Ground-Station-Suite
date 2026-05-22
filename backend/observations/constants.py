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

"""Constants for the scheduler module."""

# Tolerance window for detecting overlapping passes (in minutes)
# When checking if an observation already exists for a pass, we consider
# observations within ±PASS_OVERLAP_TOLERANCE_MINUTES of the pass window
PASS_OVERLAP_TOLERANCE_MINUTES = 5

# Default auto-generation interval (in hours)
DEFAULT_AUTO_GENERATE_INTERVAL_HOURS = 6

# Preference key for auto-generation interval
AUTO_GENERATE_INTERVAL_PREFERENCE = "scheduler.auto_generate_interval_hours"

# Observation status constants
# These match the ObservationStatus enum in db.models but are provided as strings
# for easier comparison in business logic
STATUS_SCHEDULED = "scheduled"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUS_FAILED = "failed"
STATUS_MISSED = "missed"

# All valid observation statuses
VALID_STATUSES = (
    STATUS_SCHEDULED,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_MISSED,
)

# Conflict resolution strategies
CONFLICT_STRATEGY_PRIORITY = "priority"  # Keep passes with higher peak elevation
CONFLICT_STRATEGY_SKIP = "skip"  # Skip all conflicting passes and log
CONFLICT_STRATEGY_FORCE = "force"  # Schedule anyway, allow overlaps

# Default conflict resolution strategy
DEFAULT_CONFLICT_STRATEGY = CONFLICT_STRATEGY_PRIORITY

# All valid conflict strategies
VALID_CONFLICT_STRATEGIES = (
    CONFLICT_STRATEGY_PRIORITY,
    CONFLICT_STRATEGY_SKIP,
    CONFLICT_STRATEGY_FORCE,
)
