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


class SynchronizationErrorMainTLESource(Exception):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message  # Additional storage for convenience

    def __str__(self):
        base_str = f"SynchronizationErrorMainTLESource: {self.message}"
        return base_str


class AzimuthOutOfBounds(Exception):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        base_str = f"AzimuthOutOfBounds: {self.message}"
        return base_str


class ElevationOutOfBounds(Exception):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        base_str = f"ElevationOutOfBounds: {self.message}"
        return base_str


class MinimumElevationError(Exception):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        base_str = f"MinimumElevationError: {self.message}"
        return base_str
