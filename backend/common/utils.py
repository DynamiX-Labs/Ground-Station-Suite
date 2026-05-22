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


import uuid
from typing import List


def convert_strings_to_uuids(string_uuids: List[str]) -> List[uuid.UUID]:
    """
    Converts a list of string UUIDs to a list of UUID objects.

    Parameters:
      string_uuids (List[str]): A list of strings representing UUIDs.

    Returns:
      List[uuid.UUID]: A list of UUID objects.
    """
    return [uuid.UUID(u) for u in string_uuids]
