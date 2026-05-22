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
Handler registry for mapping commands to handler functions.

This module provides a registry pattern for organizing Socket.IO command handlers,
allowing for clean separation of concerns and easier testing.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class HandlerRoute:
    """Represents a registered handler route."""

    handler: Callable
    event_type: str  # 'data_request', 'data_submission', 'sdr_data', 'file_browser'


class HandlerRegistry:
    """Registry for Socket.IO command handlers."""

    def __init__(self):
        self._routes: Dict[str, HandlerRoute] = {}

    def register(self, command: str, handler: Callable, event_type: str):
        """
        Register a command handler.

        Args:
            command: Command string (e.g., 'get-satellites')
            handler: Async function to handle the command
            event_type: Type of Socket.IO event this handles
        """
        self._routes[command] = HandlerRoute(handler, event_type)

    def get_handler(self, command: str) -> Optional[HandlerRoute]:
        """
        Get handler for a command.

        Args:
            command: Command string to look up

        Returns:
            HandlerRoute if found, None otherwise
        """
        return self._routes.get(command)

    def register_batch(self, routes: Dict[str, tuple]):
        """
        Register multiple routes at once.

        Args:
            routes: Dictionary mapping command strings to (handler, event_type) tuples
        """
        for cmd, (handler, event_type) in routes.items():
            self.register(cmd, handler, event_type)

    def get_commands_for_event_type(self, event_type: str) -> list:
        """
        Get all commands registered for a specific event type.

        Args:
            event_type: Event type to filter by

        Returns:
            List of command strings
        """
        return [cmd for cmd, route in self._routes.items() if route.event_type == event_type]


# Global registry instance
handler_registry = HandlerRegistry()
