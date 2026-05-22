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

"""Event emission helpers for scheduled observations."""

# Global socketio instance (set by startup.py)
_sio = None

# Global observation sync instance (set by startup.py)
observation_sync = None


def set_socketio_instance(sio):
    """Set the global socketio instance for event emission."""
    global _sio
    _sio = sio


async def emit_scheduled_observations_changed():
    """Emit event to all clients that scheduled observations have changed."""
    if _sio:
        await _sio.emit("scheduled-observations-changed")
