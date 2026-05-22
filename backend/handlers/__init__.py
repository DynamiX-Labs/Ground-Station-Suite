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

"""
Handlers package - refactored into entity-based modules with clean routing.

New structure:
- handlers/entities/: Entity-specific handlers (satellites, hardware, etc.)
- handlers/routing/: Routing registry and dispatcher
- handlers/socket.py: Socket.IO event registration

Legacy handlers (deprecated):
- handlers/requests.py: Use handlers/entities/* instead
- handlers/submissions.py: Use handlers/entities/* instead
- handlers/tracking.py: Moved to handlers/entities/tracking.py
"""

from .base import run_async_in_thread
from .entities import (
    appsettings,
    celestial,
    decoderconfig,
    filebrowser,
    groups,
    hardware,
    locations,
    preferences,
    satellites,
    sdr,
    tracking,
    transmitters,
)
from .entities.filebrowser import filebrowser_request_routing
from .entities.sdr import sdr_data_request_routing
from .entities.tracking import emit_tracker_data, emit_ui_tracker_values
from .routing import HandlerRegistry, dispatch_request, handler_registry

__all__ = [
    # Base utilities
    "run_async_in_thread",
    # Routing
    "handler_registry",
    "HandlerRegistry",
    "dispatch_request",
    # Entity modules
    "satellites",
    "appsettings",
    "orbitalsources.py",
    "tlesources.py",
    "groups",
    "hardware",
    "locations",
    "preferences",
    "transmitters",
    "tracking",
    "filebrowser",
    "sdr",
    "celestial",
    "decoderconfig",
    # Special routing functions (for backwards compatibility)
    "filebrowser_request_routing",
    "sdr_data_request_routing",
    # Tracking utilities
    "emit_tracker_data",
    "emit_ui_tracker_values",
]
